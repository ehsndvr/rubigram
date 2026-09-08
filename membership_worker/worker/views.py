"""The signed internal HTTP API used by the panel."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rubigram.version import __version__
from rubigram_internal.signing import SignatureError, verify_body

from .async_runtime import run_async
from .models import MembershipJob
from .services import (
    InsufficientCapacityError,
    VerifyOutcome,
    WorkerServiceError,
    available_account_count,
    cancel_pending_login,
    complete_phone_signup,
    create_membership_job,
    job_status_payload,
    remember_nonce,
    start_phone_login,
    verify_phone_code,
)

log = logging.getLogger("membership_worker.views")


def _error(message: str, *, status: int = 400, extra: Optional[dict[str, Any]] = None) -> JsonResponse:
    payload: dict[str, Any] = {"ok": False, "message": message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _signed_payload(request: HttpRequest) -> tuple[Optional[dict[str, Any]], Optional[JsonResponse]]:
    try:
        verified = verify_body(
            request.body,
            headers=request.headers,
            secret=str(settings.WORKER_SHARED_SECRET),
            max_age_seconds=int(settings.WORKER_SIGNATURE_MAX_AGE_SECONDS),
        )
    except SignatureError as exc:
        return None, _error(str(exc), status=401)
    if not remember_nonce(verified.nonce):
        return None, _error("duplicate request nonce", status=409)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, _error("invalid JSON", status=422)
    if not isinstance(payload, dict):
        return None, _error("request body must be an object", status=422)
    return payload, None


def _outcome_payload(outcome: VerifyOutcome) -> dict[str, Any]:
    return {
        "remote_account_id": outcome.remote_account_id,
        "phone": outcome.phone,
        "session_name": outcome.session_name,
        "user_id": outcome.user_id,
        "auth_id": outcome.auth_id,
        "account_status": outcome.account_status,
        "requires_signup": outcome.requires_signup,
    }


def _login_state(payload: dict[str, Any]) -> dict[str, Any]:
    # The balegram panel forwards the opaque ``grpc_cookies`` object it received from start-login.
    state = payload.get("login_state") or payload.get("grpc_cookies") or {}
    return dict(state) if isinstance(state, dict) else {}


@csrf_exempt
def internal_health_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _error("Method not allowed.", status=405)
    _, error = _signed_payload(request)
    if error:
        return error
    return JsonResponse(
        {"ok": True, "provider": str(settings.WORKER_PROVIDER), "rubigram": __version__, "available_count": available_account_count()}
    )


@csrf_exempt
def internal_orders_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")
    log.info("order_request action=%s target=%s count=%s", payload.get("action"), payload.get("target"), payload.get("count"))
    try:
        job = create_membership_job(payload)
    except InsufficientCapacityError as exc:
        return _error(
            str(exc),
            status=422,
            extra={"code": "insufficient_capacity", "requested_count": exc.requested_count, "available_count": exc.available_count},
        )
    except WorkerServiceError as exc:
        return _error(str(exc), status=422)
    return JsonResponse(
        {
            "ok": True,
            "remote_order_id": str(job.id),
            "accepted_count": job.accepted_count,
            "skipped_count": job.skipped_count,
            "status": job.status,
        },
        status=202,
    )


@csrf_exempt
def internal_order_status_view(request: HttpRequest, job_id: int) -> JsonResponse:
    if request.method != "GET":
        return _error("Method not allowed.", status=405)
    _, error = _signed_payload(request)
    if error:
        return error
    job = MembershipJob.objects.filter(id=job_id).first()
    if job is None:
        return _error("order not found", status=404)
    return JsonResponse({"ok": True, **job_status_payload(job)})


@csrf_exempt
def internal_start_login_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")
    try:
        outcome = run_async(start_phone_login(username=str(payload.get("username") or "admin"), phone=str(payload.get("phone") or "")))
    except WorkerServiceError as exc:
        return _error(str(exc), status=422)
    except Exception as exc:
        log.exception("start_login_failed")
        return _error(str(exc), status=500)
    return JsonResponse(
        {
            "ok": True,
            "transaction_hash": outcome.transaction_hash,
            "phone": outcome.phone,
            "session_name": outcome.session_name,
            "device_hash": outcome.device_hash,
            "grpc_cookies": outcome.login_state,
            "login_state": outcome.login_state,
        }
    )


@csrf_exempt
def internal_verify_code_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")
    session_name = str(payload.get("session_name") or "")
    try:
        outcome = run_async(
            verify_phone_code(
                username=str(payload.get("username") or ""),
                phone=str(payload.get("phone") or ""),
                transaction_hash=str(payload.get("transaction_hash") or ""),
                code=str(payload.get("code") or ""),
                session_name=session_name,
                login_state=_login_state(payload),
            )
        )
    except WorkerServiceError as exc:
        log.warning("verify_code_rejected session=%s error=%s", session_name[:16], exc)
        return _error(str(exc), status=422)
    except Exception as exc:
        log.exception("verify_code_failed session=%s", session_name[:16])
        return _error(str(exc), status=500)
    return JsonResponse({"ok": True, **_outcome_payload(outcome)})


@csrf_exempt
def internal_signup_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")
    try:
        outcome = run_async(
            complete_phone_signup(
                username=str(payload.get("username") or ""),
                phone=str(payload.get("phone") or ""),
                transaction_hash=str(payload.get("transaction_hash") or ""),
                display_name=str(payload.get("display_name") or ""),
                session_name=str(payload.get("session_name") or ""),
                login_state=_login_state(payload),
            )
        )
    except WorkerServiceError as exc:
        return _error(str(exc), status=422)
    except Exception as exc:
        log.exception("signup_failed")
        return _error(str(exc), status=500)
    return JsonResponse({"ok": True, **_outcome_payload(outcome)})


@csrf_exempt
def internal_cancel_login_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")
    run_async(cancel_pending_login(str(payload.get("session_name") or "")))
    return JsonResponse({"ok": True})


@csrf_exempt
def internal_available_accounts_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _error("Method not allowed.", status=405)
    _, error = _signed_payload(request)
    if error:
        return error
    return JsonResponse({"ok": True, "available_count": available_account_count()})
