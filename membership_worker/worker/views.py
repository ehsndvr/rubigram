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
    InvalidProxyUrl,
    VerifyOutcome,
    WorkerServiceError,
    account_stats,
    availability_map,
    availability_snapshot,
    available_account_count,
    cancel_pending_login,
    complete_phone_signup,
    create_membership_job,
    delete_worker_account,
    job_status_payload,
    normalize_requested_proxy,
    probe_sessions,
    remember_nonce,
    start_phone_login,
    verify_phone_code,
)

log = logging.getLogger("membership_worker.views")

#: Ceiling on one stats/health call, so a misbehaving caller cannot ask for
#: the whole table in one request. The panel pages at 400.
MAX_STATS_BATCH = 500
#: Far lower, and for a different reason: a probe holds one live connection
#: per session for as long as its timeout, so this bounds how long the
#: request runs rather than how much of the database it reads.
MAX_PROBE_BATCH = 50


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


def _requested_proxy(payload: dict[str, Any]) -> Optional[str]:
    """The exit the panel bound this call to, or ``None``.

    Absent for every caller that never picked a country, and then the worker's
    own ``WORKER_PROXY`` decides exactly as it did before.
    """
    return normalize_requested_proxy(payload.get("proxy"))


def _session_names(payload: dict[str, Any], *, limit: int) -> tuple[list[str], Optional[JsonResponse]]:
    """The ``session_names`` list, checked and capped."""
    raw = payload.get("session_names") or []
    if not isinstance(raw, list):
        return [], _error("session_names must be a list", status=422)
    names = [str(name).strip() for name in raw if str(name).strip()]
    if len(names) > limit:
        return [], _error(f"too many session names (max {limit} per call)", status=413)
    return names, None


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
        proxy = _requested_proxy(payload)
    except InvalidProxyUrl as exc:
        # The caller named an exit that cannot be used. Its mistake to fix, and
        # saying so here is the only place it reads as one: unchecked, it fails
        # inside the transport as a connection error that blames Rubika.
        return _error(str(exc), status=422)
    try:
        outcome = run_async(
            start_phone_login(
                username=str(payload.get("username") or "admin"),
                phone=str(payload.get("phone") or ""),
                proxy=proxy,
            )
        )
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
            # Where the code went, said rather than left to be assumed. Rubika
            # texts it (``SMS``) or puts it in another Rubika session
            # (``Internal``); neither is Telegram, so a panel that registers from
            # a `.session` file has to leave Rubika out of that flow.
            "sent_code_type": outcome.sent_code_type,
            "code_via_telegram": outcome.code_via_telegram,
            "code_digits_count": outcome.code_digits_count,
            "next_send_code_wait_time": outcome.next_send_code_wait_time,
            # The address Rubika actually saw. The panel measures its own hop and
            # cannot measure this one, so this is the only evidence that the exit
            # it chose is the exit that registered the number.
            "egress_ip": outcome.egress_ip,
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
        proxy = _requested_proxy(payload)
    except InvalidProxyUrl as exc:
        return _error(str(exc), status=422)
    try:
        outcome = run_async(
            verify_phone_code(
                username=str(payload.get("username") or ""),
                phone=str(payload.get("phone") or ""),
                transaction_hash=str(payload.get("transaction_hash") or ""),
                code=str(payload.get("code") or ""),
                session_name=session_name,
                login_state=_login_state(payload),
                proxy=proxy,
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
        proxy = _requested_proxy(payload)
    except InvalidProxyUrl as exc:
        return _error(str(exc), status=422)
    try:
        outcome = run_async(
            complete_phone_signup(
                username=str(payload.get("username") or ""),
                phone=str(payload.get("phone") or ""),
                transaction_hash=str(payload.get("transaction_hash") or ""),
                display_name=str(payload.get("display_name") or ""),
                session_name=str(payload.get("session_name") or ""),
                login_state=_login_state(payload),
                proxy=proxy,
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


@csrf_exempt
def internal_account_stats_view(request: HttpRequest) -> JsonResponse:
    """What the worker knows about these accounts — no Rubika connection made.

    POST body (signed):
      {"session_names": ["rubi-…"], "account_ids": [1, 2], "include_aggregate": bool}

    Answers ``{"per_account": {"<session_name>": {worker_status, last_error,
    joined, …}}}`` plus the worker-wide rollup when asked for it.  The panel
    reads ``worker_status`` and ``last_error`` to colour a row; everything else
    is there because it costs nothing extra to send.
    """
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")

    names, error = _session_names(payload, limit=MAX_STATS_BATCH)
    if error:
        return error
    raw_ids = payload.get("account_ids") or []
    if not isinstance(raw_ids, list):
        return _error("account_ids must be a list", status=422)
    try:
        ids = [int(value) for value in raw_ids]
    except (TypeError, ValueError):
        return _error("account_ids must be integers", status=422)
    if len(ids) > MAX_STATS_BATCH:
        return _error(f"too many account ids (max {MAX_STATS_BATCH} per call)", status=413)

    result = account_stats(
        session_names=names,
        account_ids=ids,
        include_aggregate=bool(payload.get("include_aggregate")),
    )
    return JsonResponse({"ok": True, **result})


@csrf_exempt
def internal_account_health_view(request: HttpRequest) -> JsonResponse:
    """What the last probe recorded — the rollup always, per account when asked.

    Reports the periodic scan's findings and never probes Rubika inline; that is
    what ``internal/accounts/probe/`` is for.  An account with no verdict yet
    comes back ``unknown`` rather than being quietly counted as healthy.
    """
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")

    names, error = _session_names(payload, limit=MAX_STATS_BATCH)
    if error:
        return error

    response: dict[str, Any] = {"ok": True, **availability_snapshot()}
    if names:
        known = availability_map(names)
        # Every name asked about gets an answer, including the ones with no row:
        # a session missing from the map reads as an error to a caller that has
        # to tell "not probed" from "not answered".
        response["per_account"] = {
            name: known.get(name, {"availability": "unknown", "outcome": "", "detail": "", "last_checked_at": None}) for name in names
        }
    return JsonResponse(response)


@csrf_exempt
def internal_account_probe_view(request: HttpRequest) -> JsonResponse:
    """Connect as each of these sessions right now and report what happened.

    ``internal/accounts/health/`` reports what the scan last found, which is
    nothing at all for an account registered a minute ago — exactly when someone
    wants to know whether the session works.  This one holds a live connection
    per session, so the batch is capped far lower and a caller wanting more
    should page.  Read-only: it authenticates and reads, and never acts as the
    account.  Verdicts are persisted, so the health rollup reflects them after.
    """
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")

    names, error = _session_names(payload, limit=MAX_PROBE_BATCH)
    if error:
        return error
    if not names:
        return _error("session_names is required", status=422)

    try:
        timeout = float(payload.get("timeout") or settings.WORKER_LOGIN_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        return _error("timeout must be a number", status=422)

    try:
        results, missing = probe_sessions(names, timeout=timeout)
    except Exception as exc:
        log.exception("account_probe_failed")
        return _error(str(exc), status=500)

    return JsonResponse(
        {
            "ok": True,
            "per_account": {
                name: {
                    "alive": result.alive,
                    "outcome": result.outcome,
                    "availability": result.availability,
                    "detail": result.detail,
                    "phone": result.phone,
                    "account_id": result.account_id,
                }
                for name, result in results.items()
            },
            # Named separately rather than left out: "this worker has no such
            # account" and "the probe failed" are different answers.
            "missing": missing,
        }
    )


@csrf_exempt
def internal_delete_account_view(request: HttpRequest) -> JsonResponse:
    """Hard-delete the worker-side account rows for a number the panel dropped.

    Accepts ``account_id``, ``session_name`` or ``phone`` — the most specific
    one given wins.  Idempotent: a row that is already gone answers
    ``deleted: 0`` with HTTP 200, so a retry after a partial failure is safe.
    """
    if request.method != "POST":
        return _error("Method not allowed.", status=405)
    payload, error = _signed_payload(request)
    if error or payload is None:
        return error or _error("invalid request")

    raw_id = payload.get("account_id")
    account_id: Optional[int] = None
    if raw_id not in (None, ""):
        try:
            account_id = int(raw_id)
        except (TypeError, ValueError):
            return _error("account_id must be an integer", status=422)

    session_name = str(payload.get("session_name") or "").strip() or None
    phone = str(payload.get("phone") or "").strip() or None
    if account_id is None and not session_name and not phone:
        return _error("one of account_id, session_name or phone is required", status=422)

    try:
        result = delete_worker_account(account_id=account_id, session_name=session_name, phone=phone)
    except WorkerServiceError as exc:
        return _error(str(exc), status=422)
    except Exception as exc:
        log.exception("delete_account_failed")
        return _error(str(exc), status=500)
    return JsonResponse({"ok": True, **result})
