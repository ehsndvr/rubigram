"""Processing one job item: claim it, pace the account, run the Rubika action, record the result."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import F
from django.utils import timezone

from . import jobs, rubika
from .models import AccountThrottle, MembershipJob, MembershipJobItem, WorkerAccount, WorkerAccountCredential

log = logging.getLogger("membership_worker.items")

RUNNING_ITEM_STALE_SECONDS = 300


def claim_item_and_reserve_throttle(item_id: int) -> Optional[int]:
    """Mark the item RUNNING.  ``None`` = go ahead, ``-1`` = drop, ``n`` = retry in n seconds."""
    now = timezone.now()
    with transaction.atomic():
        item = MembershipJobItem.objects.select_for_update().select_related("account", "job").get(id=item_id)
        if item.status == MembershipJobItem.Status.RUNNING:
            stale_cutoff = now - timedelta(seconds=RUNNING_ITEM_STALE_SECONDS)
            if item.started_at and item.started_at < stale_cutoff:
                log.warning("item_stale_reset item=%s job=%s", item.id, item.job_id)
                item.status = MembershipJobItem.Status.PENDING
                item.started_at = None
                item.save(update_fields=["status", "started_at"])
            else:
                return -1
        elif item.status != MembershipJobItem.Status.PENDING:
            return -1
        if item.job.action != MembershipJob.Action.VIEW:
            throttle, _ = AccountThrottle.objects.select_for_update().get_or_create(account=item.account)
            if throttle.next_available_at and throttle.next_available_at > now:
                return max(1, int((throttle.next_available_at - now).total_seconds()))
            throttle.next_available_at = now + timedelta(seconds=float(settings.WORKER_ACTION_DELAY_SECONDS))
            throttle.locked_at = now
            throttle.save(update_fields=["next_available_at", "locked_at", "updated_at"])
        item.status = MembershipJobItem.Status.RUNNING
        item.attempts = F("attempts") + 1
        item.started_at = now
        item.save(update_fields=["status", "attempts", "started_at"])
        return None


def finish_item(item: MembershipJobItem, *, status: str, group_title: str = "", message: str = "") -> None:
    item.status = status
    item.group_title = group_title[:255]
    item.message = message
    item.finished_at = timezone.now()
    item.save(update_fields=["status", "group_title", "message", "finished_at"])
    field = {
        MembershipJobItem.Status.SUCCESS: "success_count",
        MembershipJobItem.Status.FAILED: "failed_count",
        MembershipJobItem.Status.SKIPPED: "skipped_count",
    }.get(status)
    if field:
        MembershipJob.objects.filter(id=item.job_id).update(**{field: F(field) + 1}, updated_at=timezone.now())


def throttle_account(account: WorkerAccount, seconds: float) -> None:
    AccountThrottle.objects.update_or_create(account=account, defaults={"next_available_at": timezone.now() + timedelta(seconds=seconds)})


def disable_account(account: WorkerAccount, reason: str) -> None:
    account.status = WorkerAccount.Status.DISABLED
    account.last_error = reason[:2000]
    account.save(update_fields=["status", "last_error", "updated_at"])


def refresh_credential(account: WorkerAccount, session_string: Optional[str]) -> None:
    if session_string:
        WorkerAccountCredential.objects.update_or_create(account=account, defaults={"session_string": session_string})


def _session_string(account: WorkerAccount) -> str:
    credential = WorkerAccountCredential.objects.filter(account=account).first()
    if credential is None or not credential.session_string:
        raise rubika.ActionError(rubika.ActionError.SESSION_DEAD, "account has no stored session")
    return credential.session_string


def _run_action(item: MembershipJobItem) -> str:
    """Perform the job action for ``item`` and record success; returns the callback event."""
    job, account = item.job, item.account
    session_string = _session_string(account)
    if job.action == MembershipJob.Action.JOIN:
        outcome = rubika.run_join(
            session_name=account.session_name, session_string=session_string, target=job.target, probe_after=job.member_count_before is None
        )
        refresh_credential(account, outcome.session_string)
        jobs.save_job_member_counts(job, before=outcome.member_count_before, after=outcome.member_count_after)
        jobs.mark_membership(
            account,
            target_key=job.target_key,
            target=job.target,
            joined=True,
            title=outcome.title,
            object_guid=outcome.object_guid,
            object_type=outcome.object_type,
        )
        if not job.object_guid:
            MembershipJob.objects.filter(id=job.id, object_guid="").update(object_guid=outcome.object_guid)
        jobs.create_auto_leave_if_needed(job, item)
        finish_item(item, status=MembershipJobItem.Status.SUCCESS, group_title=outcome.title)
        return "item_success"
    if job.action == MembershipJob.Action.VIEW:
        view = rubika.run_view(
            session_name=account.session_name, session_string=session_string, target=job.target, service_id=job.service_id
        )
        refresh_credential(account, view.session_string)
        finish_item(item, status=MembershipJobItem.Status.SUCCESS, message=f"viewed {len(view.message_ids)} post(s)")
        return "item_success"
    if not jobs.WorkerMembership.objects.filter(
        account=account, target_key=job.target_key, status=jobs.WorkerMembership.Status.JOINED
    ).exists():
        finish_item(item, status=MembershipJobItem.Status.SKIPPED, message="account is not joined to target")
        return "item_skipped"
    left = rubika.run_leave(session_name=account.session_name, session_string=session_string, target=job.target)
    refresh_credential(account, left.session_string)
    jobs.mark_membership(
        account,
        target_key=job.target_key,
        target=job.target,
        joined=False,
        title=left.title,
        object_guid=left.object_guid,
        object_type=left.object_type,
    )
    finish_item(item, status=MembershipJobItem.Status.SUCCESS, group_title=left.title)
    return "item_success"


def _handle_failure(item: MembershipJobItem, error: rubika.ActionError) -> Optional[str]:
    """Record a failed action; returns the callback event, or ``None`` when the job was cancelled."""
    job, account = item.job, item.account
    kind, message = error.kind, str(error)
    if kind == rubika.ActionError.INVALID_TARGET:
        if job.success_count > 0:
            finish_item(item, status=MembershipJobItem.Status.SKIPPED, message=f"transient_target_error: {message}")
            return "item_skipped"
        finish_item(item, status=MembershipJobItem.Status.SKIPPED, message=f"invalid_target: {message}")
        jobs.cancel_job_invalid_target(job.id, reason=message)
        return None
    if kind == rubika.ActionError.ALREADY_DONE:
        if job.action == MembershipJob.Action.JOIN:
            jobs.mark_membership(account, target_key=job.target_key, target=job.target, joined=True, title=job.target)
            jobs.create_auto_leave_if_needed(job, item)
            finish_item(item, status=MembershipJobItem.Status.SUCCESS, group_title=job.target)
            return "item_success"
        if job.action == MembershipJob.Action.LEAVE:
            jobs.mark_membership(account, target_key=job.target_key, target=job.target, joined=False)
        finish_item(item, status=MembershipJobItem.Status.SKIPPED, message=message)
        return "item_skipped"
    if kind == rubika.ActionError.SESSION_DEAD:
        finish_item(item, status=MembershipJobItem.Status.SKIPPED, message=f"session_dead: {message}")
        disable_account(account, message)
        return "item_skipped"
    if kind == rubika.ActionError.THROTTLED:
        finish_item(item, status=MembershipJobItem.Status.SKIPPED, message=f"throttled: {message}")
        throttle_account(account, error.retry_after or float(settings.WORKER_THROTTLE_TOO_REQUESTS_SECONDS))
        return "item_skipped"
    if kind == rubika.ActionError.CONN_ERROR:
        finish_item(item, status=MembershipJobItem.Status.SKIPPED, message=f"conn_error: {message}")
        throttle_account(account, float(settings.WORKER_THROTTLE_CONN_ERROR_SECONDS))
        return "item_skipped"
    finish_item(item, status=MembershipJobItem.Status.FAILED, message=message)
    account.last_error = message[:2000]
    account.save(update_fields=["last_error", "updated_at"])
    return "item_failed"


def process_membership_job_item(item_id: int) -> None:
    close_old_connections()
    try:
        delay = claim_item_and_reserve_throttle(item_id)
        if delay == -1:
            return
        if delay is not None:
            from . import tasks

            tasks.process_membership_job_item_task.apply_async(args=[item_id], countdown=delay)
            return
        item = MembershipJobItem.objects.select_related("job", "account").get(id=item_id)
        try:
            event = _run_action(item)
        except Exception as exc:
            error = rubika.classify_error(exc)
            log.warning("item_failed item=%s job=%s kind=%s error=%s", item.id, item.job_id, error.kind, error)
            event = _handle_failure(item, error)
            if event is None:
                return
        log.info("item_done item=%s job=%s event=%s", item.id, item.job_id, event)
        jobs.finalize_job_if_done(item.job_id)
    finally:
        close_old_connections()


__all__ = [
    "RUNNING_ITEM_STALE_SECONDS",
    "claim_item_and_reserve_throttle",
    "disable_account",
    "finish_item",
    "process_membership_job_item",
    "refresh_credential",
    "throttle_account",
]
