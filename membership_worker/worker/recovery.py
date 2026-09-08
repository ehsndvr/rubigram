"""Periodic work: lost tasks, stuck jobs and the retention auto-leave."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from . import jobs, rubika
from .items import refresh_credential
from .models import AccountThrottle, MembershipJob, MembershipJobItem, WorkerAccountCredential, WorkerAutoLeaveSchedule

log = logging.getLogger("membership_worker.recovery")


def recover_stale_running_items() -> int:
    """RUNNING items whose worker died go back to PENDING and are re-queued."""
    from . import tasks

    cutoff = timezone.now() - timedelta(seconds=60)
    stale_ids = list(
        MembershipJobItem.objects.filter(status=MembershipJobItem.Status.RUNNING, started_at__lt=cutoff).values_list("id", flat=True)
    )
    if stale_ids:
        MembershipJobItem.objects.filter(id__in=stale_ids).update(status=MembershipJobItem.Status.PENDING)
        account_ids = list(MembershipJobItem.objects.filter(id__in=stale_ids).values_list("account_id", flat=True))
        AccountThrottle.objects.filter(account_id__in=account_ids).update(locked_at=None, next_available_at=None)
        for item_id in stale_ids:
            tasks.process_membership_job_item_task.delay(item_id)
        log.info("recover_stale_running_items reset=%d", len(stale_ids))
    return len(stale_ids)


def recover_stale_pending_items() -> int:
    """Re-dispatch PENDING items whose task message was lost from the broker."""
    from . import tasks

    cutoff = timezone.now() - timedelta(minutes=2)
    stale_ids = list(
        MembershipJobItem.objects.filter(
            status=MembershipJobItem.Status.PENDING,
            created_at__lt=cutoff,
            attempts=0,
            job__status__in=[MembershipJob.Status.PENDING, MembershipJob.Status.INPROGRESS],
        ).values_list("id", flat=True)[:200]
    )
    for item_id in stale_ids:
        tasks.process_membership_job_item_task.delay(item_id)
    if stale_ids:
        log.info("recover_stale_pending_items re-dispatched=%d", len(stale_ids))
    return len(stale_ids)


def recover_stale_inprogress_jobs() -> int:
    """Finalize INPROGRESS jobs that have no item in flight (a lost slot-fill retry)."""
    cutoff = timezone.now() - timedelta(seconds=30)
    stuck_ids = list(
        MembershipJob.objects.filter(status__in=[MembershipJob.Status.INPROGRESS, MembershipJob.Status.PENDING], updated_at__lt=cutoff)
        .exclude(items__status__in=list(jobs.RESERVED_ITEM_STATUSES))
        .values_list("id", flat=True)
        .distinct()
    )
    for job_id in stuck_ids:
        jobs.finalize_job_if_done(job_id)
    if stuck_ids:
        log.info("recover_stale_inprogress_jobs recovered=%d", len(stuck_ids))
    return len(stuck_ids)


def enqueue_due_auto_leaves(limit: int = 200) -> int:
    from . import tasks

    ids = list(
        WorkerAutoLeaveSchedule.objects.filter(status=WorkerAutoLeaveSchedule.Status.PENDING, due_at__lte=timezone.now())
        .order_by("due_at", "id")
        .values_list("id", flat=True)[:limit]
    )
    for schedule_id in ids:
        tasks.process_auto_leave_task.delay(schedule_id)
    return len(ids)


def process_auto_leave(schedule_id: int) -> None:
    schedule = WorkerAutoLeaveSchedule.objects.select_related("account", "source_job").get(id=schedule_id)
    if schedule.status != WorkerAutoLeaveSchedule.Status.PENDING or schedule.due_at > timezone.now():
        return
    schedule.status = WorkerAutoLeaveSchedule.Status.PROCESSING
    schedule.attempts += 1
    schedule.save(update_fields=["status", "attempts", "updated_at"])
    account = schedule.account
    try:
        credential = WorkerAccountCredential.objects.filter(account=account).first()
        if credential is None:
            raise rubika.ActionError(rubika.ActionError.SESSION_DEAD, "account has no stored session")
        left = rubika.run_leave(session_name=account.session_name, session_string=credential.session_string, target=schedule.target)
        refresh_credential(account, left.session_string)
        jobs.mark_membership(
            account,
            target_key=schedule.target_key,
            target=schedule.target,
            joined=False,
            title=left.title,
            object_guid=left.object_guid,
            object_type=left.object_type,
        )
    except rubika.ActionError as exc:
        if exc.kind == rubika.ActionError.ALREADY_DONE:
            jobs.mark_membership(account, target_key=schedule.target_key, target=schedule.target, joined=False)
        else:
            schedule.status = WorkerAutoLeaveSchedule.Status.FAIL
            schedule.last_error = str(exc)[:2000]
            schedule.save(update_fields=["status", "last_error", "updated_at"])
            return
    except Exception as exc:
        schedule.status = WorkerAutoLeaveSchedule.Status.FAIL
        schedule.last_error = str(exc)[:2000]
        schedule.save(update_fields=["status", "last_error", "updated_at"])
        return
    schedule.status = WorkerAutoLeaveSchedule.Status.COMPLETED
    schedule.processed_at = timezone.now()
    schedule.last_error = ""
    schedule.save(update_fields=["status", "processed_at", "last_error", "updated_at"])
    complete_active_job_if_auto_leaves_done(schedule.source_job_id)


def complete_active_job_if_auto_leaves_done(job_id: int) -> None:
    if WorkerAutoLeaveSchedule.objects.filter(
        source_job_id=job_id, status__in=[WorkerAutoLeaveSchedule.Status.PENDING, WorkerAutoLeaveSchedule.Status.PROCESSING]
    ).exists():
        return
    job = MembershipJob.objects.get(id=job_id)
    if job.status != MembershipJob.Status.ACTIVE:
        return
    job.status = MembershipJob.Status.COMPLETED
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "finished_at", "updated_at"])
    from . import tasks

    tasks.send_membership_callback_task.delay(job.id, "order_completed")


__all__ = [
    "complete_active_job_if_auto_leaves_done",
    "enqueue_due_auto_leaves",
    "process_auto_leave",
    "recover_stale_inprogress_jobs",
    "recover_stale_pending_items",
    "recover_stale_running_items",
]
