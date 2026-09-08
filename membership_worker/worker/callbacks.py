"""Signed status callbacks from the worker to the panel."""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from django.conf import settings

from rubigram_internal.signing import sign_json

from .accounts import WorkerServiceError
from .jobs import build_callback_payload
from .models import MembershipJob, MembershipJobItem

log = logging.getLogger("membership_worker.callbacks")


def send_membership_callback(job_id: int, event_type: str, item_id: Optional[int] = None) -> None:
    """POST one event to the job's ``callback_url``; raises so Celery retries on failure."""
    job = MembershipJob.objects.get(id=job_id)
    item = MembershipJobItem.objects.filter(id=item_id).first() if item_id else None
    payload = build_callback_payload(job, event_type, item)
    body, headers = sign_json(
        payload, secret=str(settings.WORKER_SHARED_SECRET), header_prefix=str(settings.WORKER_SIGNATURE_HEADER_PREFIX)
    )
    try:
        response = httpx.post(job.callback_url, content=body, headers=headers, timeout=float(settings.WORKER_CALLBACK_TIMEOUT_SECONDS))
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("callback_failed job=%s event=%s error=%s", job_id, event_type, exc)
        raise WorkerServiceError(str(exc)) from exc
    log.info("callback_sent job=%s event=%s status=%s", job_id, event_type, response.status_code)


__all__ = ["send_membership_callback"]
