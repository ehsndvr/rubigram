"""Jobs: creating an order, choosing accounts, finishing and reporting it."""

from __future__ import annotations

import logging
import math
from datetime import timedelta
from typing import Any, Optional

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .accounts import WorkerServiceError
from .models import (
    AccountThrottle,
    MembershipJob,
    MembershipJobItem,
    WorkerAccount,
    WorkerAutoLeaveSchedule,
    WorkerMembership,
    WorkerSignedNonce,
)
from .targets import TargetError, normalize_target_key

log = logging.getLogger("membership_worker.jobs")

ACTIVE_JOB_STATUSES = {MembershipJob.Status.ACTIVE, MembershipJob.Status.INPROGRESS, MembershipJob.Status.PENDING}
RESERVED_ITEM_STATUSES = {MembershipJobItem.Status.PENDING, MembershipJobItem.Status.RUNNING}
TERMINAL_JOB_STATUSES = {
    MembershipJob.Status.FAIL,
    MembershipJob.Status.PARTIAL,
    MembershipJob.Status.COMPLETED,
    MembershipJob.Status.ERROR,
}
RETRYABLE_SKIP_PREFIXES = ("conn_error:", "throttled:")  # the account stays usable for the same job


class InsufficientCapacityError(WorkerServiceError):
    def __init__(self, *, requested_count: int, available_count: int) -> None:
        super().__init__("Insufficient available accounts for target.")
        self.requested_count = requested_count
        self.available_count = available_count


def apply_bonus(count: int) -> int:
    """Join orders get ``WORKER_BONUS_PERCENTAGE`` extra members as a quality buffer."""
    bonus = float(settings.WORKER_BONUS_PERCENTAGE)
    return count + math.ceil(count * bonus / 100) if bonus > 0 else count


def optional_positive_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def remember_nonce(nonce: str) -> bool:
    try:
        WorkerSignedNonce.objects.create(nonce=nonce)
    except IntegrityError:
        return False
    return True


# ── account selection ────────────────────────────────────────────────────────────


def select_accounts(
    *, action: str, target_key: str, count: int, exclude_account_ids: Optional[list[int]] = None, lock: bool = False
) -> list[WorkerAccount]:
    now = timezone.now()
    throttled_ids = AccountThrottle.objects.filter(next_available_at__gt=now).values("account_id")
    active = WorkerAccount.objects.filter(status=WorkerAccount.Status.ACTIVE).exclude(id__in=throttled_ids).order_by("id")
    if lock:
        active = active.select_for_update(skip_locked=True)
    if exclude_account_ids:
        active = active.exclude(id__in=exclude_account_ids)
    if action == MembershipJob.Action.JOIN:
        joined_ids = WorkerMembership.objects.filter(target_key=target_key, status=WorkerMembership.Status.JOINED).values_list(
            "account_id", flat=True
        )
        reserved_ids = MembershipJobItem.objects.filter(
            job__action=MembershipJob.Action.JOIN,
            job__target_key=target_key,
            job__status__in=ACTIVE_JOB_STATUSES,
            status__in=RESERVED_ITEM_STATUSES,
        ).values_list("account_id", flat=True)
        return list(active.exclude(id__in=joined_ids).exclude(id__in=reserved_ids)[:count])
    if action == MembershipJob.Action.VIEW:
        pool_qs = WorkerAccount.objects.filter(status=WorkerAccount.Status.ACTIVE).order_by("id")
        if lock:
            pool_qs = pool_qs.select_for_update(skip_locked=True)
        if exclude_account_ids:
            pool_qs = pool_qs.exclude(id__in=exclude_account_ids)
        pool = list(pool_qs)
        return [pool[i % len(pool)] for i in range(count)] if pool else []
    memberships = (
        WorkerMembership.objects.filter(
            target_key=target_key, status=WorkerMembership.Status.JOINED, account__status=WorkerAccount.Status.ACTIVE
        )
        .select_related("account")
        .order_by("-joined_at", "-updated_at")[:count]
    )
    return [membership.account for membership in memberships]


# ── creation ──────────────────────────────────────────────────────────────────────


def create_membership_job(payload: dict[str, Any]) -> MembershipJob:
    """Validate a panel order, reserve accounts and enqueue the items (idempotent on ``idempotency_key``)."""
    try:
        external_order_id = int(payload["external_order_id"])
        requested_count = int(payload["count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkerServiceError("external_order_id and count are required integers") from exc
    if requested_count < 1:
        raise WorkerServiceError("count must be positive")
    action = str(payload.get("action") or "").strip()
    if action not in {MembershipJob.Action.JOIN, MembershipJob.Action.LEAVE, MembershipJob.Action.VIEW}:
        raise WorkerServiceError("unsupported action")
    target = str(payload.get("target") or "").strip()
    try:
        target_key = normalize_target_key(target)
    except TargetError as exc:
        raise WorkerServiceError(str(exc)) from exc
    callback_url = str(payload.get("callback_url") or "").strip()
    if not callback_url:
        raise WorkerServiceError("callback_url is required")
    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if not idempotency_key:
        raise WorkerServiceError("idempotency_key is required")

    existing = MembershipJob.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    target_count = apply_bonus(requested_count) if action == MembershipJob.Action.JOIN else requested_count
    now = timezone.now()
    try:
        with transaction.atomic():
            accounts = select_accounts(action=action, target_key=target_key, count=target_count, lock=True)
            accepted = len(accounts)
            log.info(
                "create_job target=%s action=%s requested=%s total=%s accepted=%s",
                target_key,
                action,
                requested_count,
                target_count,
                accepted,
            )
            if action == MembershipJob.Action.JOIN and accepted == 0:
                raise InsufficientCapacityError(requested_count=requested_count, available_count=0)
            job = MembershipJob.objects.create(
                external_order_id=external_order_id,
                idempotency_key=idempotency_key,
                action=action,
                target=target,
                target_key=target_key,
                requested_count=requested_count,
                total_count=target_count,
                accepted_count=accepted,
                skipped_count=max(0, target_count - accepted),
                status=MembershipJob.Status.INPROGRESS if accounts else MembershipJob.Status.FAIL,
                service_id=str(payload.get("service_id") or ""),
                retention_days=optional_positive_int(payload.get("retention_days")),
                callback_url=callback_url,
                started_at=now if accounts else None,
                finished_at=None if accounts else now,
            )
            MembershipJobItem.objects.bulk_create(MembershipJobItem(job=job, account=account) for account in accounts)
    except IntegrityError:
        # a concurrent retry with the same idempotency_key won the race
        return MembershipJob.objects.get(idempotency_key=idempotency_key)

    from . import tasks

    tasks.send_membership_callback_task.delay(job.id, "order_accepted")
    for item_id in MembershipJobItem.objects.filter(job=job).values_list("id", flat=True):
        tasks.process_membership_job_item_task.delay(item_id)
    if not accounts:
        tasks.send_membership_callback_task.delay(job.id, "order_failed")
    return job


# ── bookkeeping ───────────────────────────────────────────────────────────────────


def save_job_member_counts(job: MembershipJob, *, before: Optional[int], after: Optional[int]) -> None:
    fields: list[str] = []
    if before is not None and job.member_count_before is None:
        job.member_count_before = before
        fields.append("member_count_before")
    if after is not None:
        job.member_count_after = after
        fields.append("member_count_after")
    if fields:
        job.save(update_fields=[*fields, "updated_at"])


def mark_membership(
    account: WorkerAccount, *, target_key: str, target: str, joined: bool, title: str = "", object_guid: str = "", object_type: str = ""
) -> None:
    membership, _ = WorkerMembership.objects.get_or_create(account=account, target_key=target_key, defaults={"target_display": target})
    membership.target_display = target
    membership.status = WorkerMembership.Status.JOINED if joined else WorkerMembership.Status.LEFT
    membership.group_title = title or membership.group_title
    membership.object_guid = object_guid or membership.object_guid
    membership.object_type = object_type or membership.object_type
    now = timezone.now()
    if joined:
        membership.joined_at = now
        membership.left_at = None
    else:
        membership.left_at = now
    membership.save()


def create_auto_leave_if_needed(job: MembershipJob, item: MembershipJobItem) -> None:
    if job.action != MembershipJob.Action.JOIN or not job.retention_days:
        return
    WorkerAutoLeaveSchedule.objects.get_or_create(
        source_item=item,
        defaults={
            "source_job": job,
            "account": item.account,
            "target": job.target,
            "target_key": job.target_key,
            "due_at": timezone.now() + timedelta(days=job.retention_days),
        },
    )


def refresh_job_counts(job_id: int) -> None:
    counts = {
        status: MembershipJobItem.objects.filter(job_id=job_id, status=status).count()
        for status in (MembershipJobItem.Status.SUCCESS, MembershipJobItem.Status.FAILED, MembershipJobItem.Status.SKIPPED)
    }
    with transaction.atomic():
        job = MembershipJob.objects.select_for_update().get(id=job_id)
        unavailable = max(0, job.total_count - job.accepted_count)
        job.success_count = counts[MembershipJobItem.Status.SUCCESS]
        job.failed_count = counts[MembershipJobItem.Status.FAILED]
        job.skipped_count = max(job.skipped_count, unavailable + counts[MembershipJobItem.Status.SKIPPED])
        job.save(update_fields=["success_count", "failed_count", "skipped_count", "updated_at"])


def cancel_job_invalid_target(job_id: int, *, reason: str) -> None:
    """Stop a job whose target is wrong for everyone; PARTIAL if some accounts already succeeded."""
    now = timezone.now()
    with transaction.atomic():
        job = MembershipJob.objects.select_for_update().get(id=job_id)
        if job.status in TERMINAL_JOB_STATUSES:
            return
        MembershipJobItem.objects.filter(job_id=job_id, status__in=RESERVED_ITEM_STATUSES).update(
            status=MembershipJobItem.Status.SKIPPED, message=f"invalid_target: {reason}", finished_at=now
        )
        had_successes = job.success_count > 0
        job.status = MembershipJob.Status.PARTIAL if had_successes else MembershipJob.Status.FAIL
        job.last_error = f"invalid_target: {reason}"
        job.finished_at = now
        job.save(update_fields=["status", "last_error", "finished_at", "updated_at"])
    refresh_job_counts(job_id)
    log.warning("job_cancelled_invalid_target job=%s reason=%s", job_id, reason)
    from . import tasks

    tasks.send_membership_callback_task.delay(job_id, "order_partial" if had_successes else "order_failed")


def enqueue_replacement_items_if_needed(job_id: int) -> Optional[list[int]]:
    """New item ids for missing join slots, ``[]`` when nothing to do, ``None`` when deferred."""
    with transaction.atomic():
        job = MembershipJob.objects.select_for_update().get(id=job_id)
        if job.action != MembershipJob.Action.JOIN or job.status not in {
            MembershipJob.Status.PENDING,
            MembershipJob.Status.INPROGRESS,
            MembershipJob.Status.ERROR,
        }:
            return []
        in_flight = MembershipJobItem.objects.filter(job=job, status__in=RESERVED_ITEM_STATUSES).count()
        missing = max(0, job.total_count - job.success_count - in_flight)
        if missing <= 0:
            return []
        used_qs = MembershipJobItem.objects.filter(job=job)
        for prefix in RETRYABLE_SKIP_PREFIXES:
            used_qs = used_qs.exclude(status=MembershipJobItem.Status.SKIPPED, message__startswith=prefix)
        permanently_used = list(used_qs.values_list("account_id", flat=True))
        accounts = select_accounts(
            action=job.action, target_key=job.target_key, count=missing, exclude_account_ids=permanently_used, lock=True
        )
        if not accounts:
            already_joined = WorkerMembership.objects.filter(target_key=job.target_key, status=WorkerMembership.Status.JOINED).values(
                "account_id"
            )
            potential = (
                WorkerAccount.objects.filter(status=WorkerAccount.Status.ACTIVE)
                .exclude(id__in=already_joined)
                .exclude(id__in=permanently_used)
                .count()
            )
            if potential == 0:
                log.warning("job_pool_exhausted job=%s target=%s missing=%s", job_id, job.target_key, missing)
                return []
            max_age = timedelta(hours=int(settings.WORKER_JOB_MAX_WAIT_HOURS))
            if job.started_at and (timezone.now() - job.started_at) < max_age:
                from . import tasks

                tasks.retry_job_slot_fill_task.apply_async(args=[job_id], countdown=90)
                return None
            return []
        item_ids = [MembershipJobItem.objects.create(job=job, account=account).id for account in accounts]
        job.accepted_count += len(item_ids)
        job.status = MembershipJob.Status.INPROGRESS
        job.finished_at = None
        job.save(update_fields=["accepted_count", "status", "finished_at", "updated_at"])
        return item_ids


def finalize_job_if_done(job_id: int) -> None:
    """When no item is pending or running: fill missing slots, else settle the job and notify the panel."""
    if MembershipJobItem.objects.filter(job_id=job_id, status__in=RESERVED_ITEM_STATUSES).exists():
        return
    refresh_job_counts(job_id)
    replacements = enqueue_replacement_items_if_needed(job_id)
    if replacements is None:
        return
    from . import tasks

    if replacements:
        for item_id in replacements:
            tasks.process_membership_job_item_task.delay(item_id)
        return
    with transaction.atomic():
        job = MembershipJob.objects.select_for_update().get(id=job_id)
        if job.status in TERMINAL_JOB_STATUSES:
            return
        if job.success_count >= job.requested_count and job.action == MembershipJob.Action.JOIN and job.retention_days:
            job.status = MembershipJob.Status.ACTIVE
        elif job.success_count >= job.requested_count:
            job.status = MembershipJob.Status.COMPLETED
        elif job.success_count > 0:
            job.status = MembershipJob.Status.PARTIAL
        else:
            job.status = MembershipJob.Status.FAIL
        if job.status != MembershipJob.Status.ACTIVE:
            job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at", "updated_at"])
    event = {
        MembershipJob.Status.COMPLETED: "order_completed",
        MembershipJob.Status.PARTIAL: "order_partial",
        MembershipJob.Status.FAIL: "order_failed",
        MembershipJob.Status.ACTIVE: "order_active",
    }[job.status]
    tasks.send_membership_callback_task.delay(job.id, event)


# ── payloads ──────────────────────────────────────────────────────────────────────


def build_callback_payload(job: MembershipJob, event_type: str, item: Optional[MembershipJobItem] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": f"{event_type}-{job.id}-{item.id if item else 'job'}",
        "event": event_type,
        "external_order_id": job.external_order_id,
        "remote_order_id": str(job.id),
        "provider": str(settings.WORKER_PROVIDER),
        "status": job.status,
        "total_count": job.total_count,
        "accepted_count": job.accepted_count,
        "success_count": job.success_count,
        "failed_count": job.failed_count,
        "skipped_count": job.skipped_count,
        "member_count_before": job.member_count_before,
        "member_count_after": job.member_count_after,
        "timestamp": timezone.now().isoformat(),
    }
    if item is not None:
        payload.update(
            {
                "item_id": item.id,
                "account_id": str(item.account_id),
                "item_status": item.status,
                "message": item.message,
                "group_title": item.group_title,
            }
        )
    return payload


def job_status_payload(job: MembershipJob) -> dict[str, Any]:
    return {
        "remote_order_id": str(job.id),
        "external_order_id": job.external_order_id,
        "status": job.status,
        "total_count": job.total_count,
        "accepted_count": job.accepted_count,
        "success_count": job.success_count,
        "failed_count": job.failed_count,
        "skipped_count": job.skipped_count,
        "member_count_before": job.member_count_before,
        "member_count_after": job.member_count_after,
    }


__all__ = [
    "ACTIVE_JOB_STATUSES",
    "RESERVED_ITEM_STATUSES",
    "RETRYABLE_SKIP_PREFIXES",
    "TERMINAL_JOB_STATUSES",
    "InsufficientCapacityError",
    "apply_bonus",
    "build_callback_payload",
    "cancel_job_invalid_target",
    "create_auto_leave_if_needed",
    "create_membership_job",
    "enqueue_replacement_items_if_needed",
    "finalize_job_if_done",
    "job_status_payload",
    "mark_membership",
    "optional_positive_int",
    "refresh_job_counts",
    "remember_nonce",
    "save_job_member_counts",
    "select_accounts",
]
