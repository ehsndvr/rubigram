"""Celery tasks.  Names and queues match the balegram worker so the same deployment recipes apply."""

from __future__ import annotations

from typing import Optional

from celery import shared_task


@shared_task(name="membership_worker.process_membership_job_item", queue="membership", soft_time_limit=120, time_limit=150)
def process_membership_job_item_task(item_id: int) -> None:
    from .items import process_membership_job_item

    process_membership_job_item(item_id)


@shared_task(
    bind=True,
    name="membership_worker.send_callback",
    queue="callbacks",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=8,
    soft_time_limit=30,
    time_limit=45,
)
def send_membership_callback_task(self, job_id: int, event_type: str, item_id: Optional[int] = None) -> None:
    from .callbacks import send_membership_callback

    send_membership_callback(job_id, event_type, item_id)


@shared_task(name="membership_worker.enqueue_due_auto_leaves", queue="default")
def enqueue_due_auto_leaves_task() -> int:
    from .recovery import enqueue_due_auto_leaves

    return enqueue_due_auto_leaves()


@shared_task(
    bind=True,
    name="membership_worker.process_auto_leave",
    queue="membership",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=120,
    time_limit=150,
)
def process_auto_leave_task(self, schedule_id: int) -> None:
    from .recovery import process_auto_leave

    process_auto_leave(schedule_id)


@shared_task(name="membership_worker.recover_stale_running_items", queue="default")
def recover_stale_running_items_task() -> int:
    from .recovery import recover_stale_running_items

    return recover_stale_running_items()


@shared_task(name="membership_worker.recover_stale_pending_items", queue="default")
def recover_stale_pending_items_task() -> int:
    from .recovery import recover_stale_pending_items

    return recover_stale_pending_items()


@shared_task(name="membership_worker.recover_stale_inprogress_jobs", queue="default")
def recover_stale_inprogress_jobs_task() -> int:
    from .recovery import recover_stale_inprogress_jobs

    return recover_stale_inprogress_jobs()


@shared_task(name="membership_worker.retry_job_slot_fill", queue="membership", soft_time_limit=120, time_limit=150)
def retry_job_slot_fill_task(job_id: int) -> None:
    """Deferred slot fill for jobs whose accounts were all throttled."""
    from .jobs import finalize_job_if_done

    finalize_job_if_done(job_id)


@shared_task(name="membership_worker.scan_account_health", queue="default", soft_time_limit=600, time_limit=660)
def scan_account_health_task(limit: int = 100) -> int:
    """Probe the accounts nobody has looked at for longest.

    On the ``default`` queue rather than ``membership``: it opens connections but
    never acts as an account, and a health sweep must not sit behind a queue of
    join orders — the moment its answer is worth having is the moment the joins
    are failing.
    """
    from .health import scan_accounts

    return scan_accounts(limit=limit)
