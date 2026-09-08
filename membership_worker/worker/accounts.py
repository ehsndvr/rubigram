"""Adding accounts: the phone login flow driven by the panel, and account rows.

The panel calls ``start-login`` (→ ``sendCode``), then ``verify-code``
(→ ``signIn``) and, for a phone without an account, ``signup``.  Between the
calls the pending client is kept in memory *and* its state is returned to the
panel as an opaque ``login_state`` (a rubigram session string without ``auth``:
the temporary session, the login key pair and the DC list), so any worker
process can finish a login that another one started.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections, models, transaction

from rubigram import Client, errors
from rubigram.utils import normalize_phone_number

from .exit import measured_egress
from .models import AccountThrottle, WorkerAccount, WorkerAccountCredential, WorkerMembership
from .rubika import build_client, worker_device_hash

log = logging.getLogger("membership_worker.accounts")


class WorkerServiceError(RuntimeError):
    """A user-facing failure; the message is shown by the panel (Persian)."""


@dataclass(frozen=True)
class StartAuthOutcome:
    transaction_hash: str  # Rubika's phone_code_hash
    phone: str
    session_name: str
    device_hash: str
    login_state: dict[str, str]

    #: What Rubika said it did with the code — ``SMS`` or ``Internal``.  Neither
    #: is Telegram, and that is the fact the panel needs: Bale and Soroush hand a
    #: foreign number's code to Telegram, which is what lets a panel register
    #: from a ``.session`` file with nobody typing anything.  Rubika never does,
    #: so a caller waiting for one waits until the code has expired.
    sent_code_type: Optional[str] = None
    #: How many digits that code has, straight from ``sendCode``.  Rubika sends
    #: five; reported rather than assumed, so a caller's input box is right even
    #: on the day it changes.
    code_digits_count: Optional[int] = None
    #: Seconds Rubika will refuse a resend for, when it says.
    next_send_code_wait_time: Optional[int] = None
    #: Always false, and sent anyway: a field that is missing reads as "unknown"
    #: to the panel, and this is known.
    code_via_telegram: bool = False
    #: The address Rubika actually saw, measured on the hop the panel cannot
    #: reach.  ``None`` when the echo service could not be asked — never a
    #: reason to fail a login.
    egress_ip: Optional[str] = None


@dataclass(frozen=True)
class VerifyOutcome:
    remote_account_id: Optional[str] = None
    phone: Optional[str] = None
    session_name: Optional[str] = None
    user_id: Optional[int] = None  # Rubika has no numeric user id; kept for the panel contract
    auth_id: Optional[str] = None  # the Rubika user guid
    account_status: str = WorkerAccount.Status.ACTIVE
    requires_signup: bool = False


_PENDING: dict[str, dict[str, Any]] = {}
_VERIFY_LOCKS: dict[str, asyncio.Lock] = {}


def normalize_verification_code(raw_value: str) -> str:
    """Keep digits only, converting Persian/Arabic digits to ASCII."""
    digits: list[str] = []
    for char in str(raw_value):
        try:
            digits.append(str(unicodedata.digit(char)))
        except (TypeError, ValueError):
            continue
    return "".join(digits)


def normalize_display_name(raw_value: str) -> str:
    return " ".join(str(raw_value).strip().split())


def build_session_name(username: str) -> str:
    safe = "".join(char if char.isalnum() else "-" for char in username.lower()).strip("-") or "user"
    return f"rubi-{safe}-{secrets.token_hex(3)}"


def _login_error(exc: Exception) -> WorkerServiceError:
    if isinstance(exc, errors.CodeIsInvalid):
        return WorkerServiceError("کد تایید نادرست است")
    if isinstance(exc, errors.CodeIsExpired):
        return WorkerServiceError("کد تایید منقضی شده است")
    if isinstance(exc, errors.CodeIsUsed):
        return WorkerServiceError("این کد قبلاً استفاده شده است")
    if isinstance(exc, errors.TooRequests):
        wait = f" {int(exc.retry_after)} ثانیه" if exc.retry_after else " چند دقیقه"
        return WorkerServiceError(f"تعداد تلاش‌ها بیش از حد مجاز است. لطفاً{wait} صبر کنید")
    if isinstance(exc, errors.InvalidInput):
        return WorkerServiceError("شماره یا کد وارد شده نامعتبر است")
    if isinstance(exc, errors.NetworkError | errors.TransportError):
        return WorkerServiceError("ارتباط با روبیکا برقرار نشد؛ دوباره تلاش کنید")
    return WorkerServiceError(str(exc) or type(exc).__name__)


async def _forget(session_name: str) -> None:
    pending = _PENDING.pop(session_name, None)
    _VERIFY_LOCKS.pop(session_name, None)
    if pending is not None:
        try:
            await pending["client"].stop()
        except Exception:
            log.debug("closing pending login client %s failed", session_name[:16], exc_info=True)


async def start_phone_login(*, username: str, phone: str, proxy: Optional[str] = None) -> StartAuthOutcome:
    """``sendCode`` for ``phone`` with a fresh temporary session.

    ``proxy`` is the exit the caller bound this registration to.  It is carried
    all the way to the Rubika connection and then repeated in ``login_state``, so
    the verify that follows leaves from the same address: a login started from
    one country and answered from another is a login the platform has every
    reason to refuse — and the second half would otherwise silently fall back to
    this worker's own address.
    """
    normalized_phone = normalize_phone_number(phone)
    if not normalized_phone:
        raise WorkerServiceError("شماره تلفن نامعتبر است")
    session_name = build_session_name(username)
    # Measured before the code is asked for, because afterwards it is too late
    # to be useful: the OTP has been spent on whatever address this turns out
    # to be, and the panel's only other evidence is its own hop, which is not
    # the one Rubika sees.
    #
    # Only when an exit is actually in play — the caller's, or this worker's own
    # default. A direct connection leaves from this machine's address, which is
    # the same for every registration and knowable without spending an HTTP
    # round trip in front of each OTP.
    exit_proxy = proxy or str(settings.WORKER_PROXY) or None
    egress_ip = await measured_egress(exit_proxy, session_name=session_name) if exit_proxy else None
    client = build_client(session_name, timeout=float(settings.WORKER_LOGIN_TIMEOUT_SECONDS), proxy=proxy)
    try:
        await client.start()
        sent = await client.send_code(normalized_phone)
    except errors.RubigramError as exc:
        await client.stop()
        raise _login_error(exc) from exc
    except Exception:
        await client.stop()
        raise
    if sent.status == "SendPassKey":
        await client.stop()
        raise WorkerServiceError("این حساب رمز دومرحله‌ای دارد و از پنل قابل افزودن نیست")
    if not sent.phone_code_hash:
        await client.stop()
        raise WorkerServiceError(f"ارسال کد تایید انجام نشد ({sent.status or 'no status'})")
    login_state = await client.export_session_string()
    _PENDING[session_name] = {"client": client, "phone": normalized_phone, "username": username, "proxy": proxy}
    log.info("start_login session=%s send_type=%s egress=%s", session_name[:16], sent.send_type, egress_ip or "?")
    return StartAuthOutcome(
        transaction_hash=str(sent.phone_code_hash),
        phone=normalized_phone,
        session_name=session_name,
        device_hash=worker_device_hash(),
        login_state={
            "login_state": login_state,
            "phone": normalized_phone,
            "username": username,
            # Round-tripped through the panel so a verify handled by a different
            # worker process still leaves from the exit the code went out on.
            "proxy": proxy or "",
        },
        sent_code_type=str(sent.send_type) if sent.send_type else None,
        code_digits_count=_optional_int(getattr(sent, "code_digits_count", None)),
        next_send_code_wait_time=_optional_int(getattr(sent, "next_send_code_wait_time", None)),
        egress_ip=egress_ip,
    )


def _optional_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def _login_client(
    session_name: str, login_state: Optional[dict[str, Any]], *, proxy: Optional[str] = None
) -> tuple[Client, dict[str, Any]]:
    pending = _PENDING.get(session_name)
    if pending is not None:
        return pending["client"], pending
    state = str((login_state or {}).get("login_state") or "")
    if not state:
        raise WorkerServiceError("نشست ورود منقضی شده است؛ شماره را دوباره وارد کنید")
    # The caller's exit wins, then the one start-login recorded. The second is
    # what makes a login survive being finished by another worker process:
    # without it the resumed half goes out from this machine's own address.
    exit_proxy = proxy or str((login_state or {}).get("proxy") or "") or None
    client = build_client(session_name, state, timeout=float(settings.WORKER_LOGIN_TIMEOUT_SECONDS), proxy=exit_proxy)
    await client.start()
    pending = {
        "client": client,
        "phone": str((login_state or {}).get("phone") or ""),
        "username": str((login_state or {}).get("username") or ""),
        "proxy": exit_proxy,
    }
    _PENDING[session_name] = pending
    return client, pending


async def _finish_login(client: Client, *, session_name: str, username: str, phone: str) -> VerifyOutcome:
    user_guid = await client.storage.user_guid() or ""
    display_name = ""
    try:
        me = await client.get_me()
        user = getattr(me, "user", None)
        if user is not None:
            user_guid = user.user_guid or user_guid
            display_name = " ".join(part for part in (user.first_name, user.last_name) if part)
    except errors.RubigramError as exc:
        log.warning("get_me after login failed session=%s: %s", session_name[:16], exc)
    session_string = await client.export_session_string()
    await _forget(session_name)
    try:
        account = await asyncio.wait_for(
            sync_to_async(save_account, thread_sensitive=False)(
                username=username,
                phone=phone,
                session_name=session_name,
                session_string=session_string,
                user_guid=user_guid,
                display_name=display_name,
            ),
            timeout=20,
        )
    except asyncio.TimeoutError as exc:
        raise WorkerServiceError("ذخیره حساب بیش از حد طول کشید") from exc
    return VerifyOutcome(
        remote_account_id=str(account.id), phone=account.phone, session_name=account.session_name, auth_id=account.user_guid or None
    )


async def verify_phone_code(
    *,
    username: str,
    phone: str,
    transaction_hash: str,
    code: str,
    session_name: str,
    login_state: Optional[dict[str, Any]] = None,
    proxy: Optional[str] = None,
) -> VerifyOutcome:
    """``signIn``; stores the account on success, ``requires_signup`` when the phone has no account."""
    normalized_code = normalize_verification_code(code)
    if not normalized_code:
        raise WorkerServiceError("کد تایید را فقط با عدد وارد کنید")
    lock = _VERIFY_LOCKS.setdefault(session_name, asyncio.Lock())
    async with lock:
        client, pending = await _login_client(session_name, login_state, proxy=proxy)
        username = username or pending.get("username", "")
        phone = normalize_phone_number(phone or pending.get("phone", "")) or ""
        try:
            await client.sign_in(phone, transaction_hash, normalized_code)
        except errors.RubigramError as exc:
            if isinstance(exc, errors.CodeIsInvalid | errors.CodeIsExpired | errors.CodeIsUsed | errors.TooRequests):
                raise _login_error(exc) from exc
            await _forget(session_name)
            raise _login_error(exc) from exc
        except Exception:
            await _forget(session_name)
            raise
        if not await client.storage.auth():
            log.info("verify_code requires signup session=%s", session_name[:16])
            return VerifyOutcome(phone=phone, session_name=session_name, requires_signup=True)
        return await _finish_login(client, session_name=session_name, username=username, phone=phone)


async def complete_phone_signup(
    *,
    username: str,
    phone: str,
    transaction_hash: str,
    display_name: str,
    session_name: str,
    login_state: Optional[dict[str, Any]] = None,
    proxy: Optional[str] = None,
) -> VerifyOutcome:
    """``signUp`` for a phone without an account (unverified against the live server)."""
    name = normalize_display_name(display_name)
    if not name:
        raise WorkerServiceError("برای تکمیل ثبت‌نام، یک نام وارد کنید")
    client, pending = await _login_client(session_name, login_state, proxy=proxy)
    username = username or pending.get("username", "")
    phone = normalize_phone_number(phone or pending.get("phone", "")) or ""
    try:
        await client.sign_up(name)
    except errors.RubigramError as exc:
        await _forget(session_name)
        raise _login_error(exc) from exc
    except Exception:
        await _forget(session_name)
        raise
    if not await client.storage.auth():
        await _forget(session_name)
        raise WorkerServiceError("ثبت‌نام کامل نشد")
    return await _finish_login(client, session_name=session_name, username=username, phone=phone)


async def cancel_pending_login(session_name: Optional[str]) -> None:
    if session_name:
        await _forget(session_name)


def save_account(*, username: str, phone: str, session_name: str, session_string: str, user_guid: str, display_name: str) -> WorkerAccount:
    """Create the account row, or refresh the existing row of the same phone."""
    close_old_connections()
    with transaction.atomic():
        existing = WorkerAccount.objects.select_for_update().filter(phone=phone).order_by("-created_at").first()
        if existing is not None:
            existing.username = username or existing.username
            existing.session_name = session_name
            existing.user_guid = user_guid or existing.user_guid
            existing.display_name = display_name or existing.display_name
            existing.status = WorkerAccount.Status.ACTIVE
            existing.last_error = ""
            existing.save()
            WorkerAccountCredential.objects.update_or_create(account=existing, defaults={"session_string": session_string})
            AccountThrottle.objects.get_or_create(account=existing)
            return existing
        account = WorkerAccount.objects.create(
            username=username,
            phone=phone,
            session_name=session_name,
            user_guid=user_guid,
            display_name=display_name,
        )
        WorkerAccountCredential.objects.create(account=account, session_string=session_string)
        AccountThrottle.objects.create(account=account)
        return account


def available_account_count() -> int:
    return WorkerAccount.objects.filter(status=WorkerAccount.Status.ACTIVE).count()


def account_stats(
    *,
    session_names: Optional[list[str]] = None,
    account_ids: Optional[list[int]] = None,
    include_aggregate: bool = False,
) -> dict[str, Any]:
    """What the worker knows about these accounts, without touching Rubika.

    Two queries whatever the caller asks about, and that is the point: the panel
    asks about a page of numbers at a time, and a stats call that ran a query per
    account would get slower every time somebody registered one.

    ``worker_status`` is deliberately the account's own ``status`` — what the job
    pipeline last ran into — and not the health verdict.  They answer different
    questions and the panel shows both: this one says "the worker stopped using
    it", ``internal/accounts/health/`` says "we connected and looked".
    """
    close_old_connections()
    rows = WorkerAccount.objects.all()
    if session_names is not None or account_ids is not None:
        query = models.Q()
        if session_names:
            query |= models.Q(session_name__in=session_names)
        if account_ids:
            query |= models.Q(id__in=account_ids)
        # Asked about nothing in particular is not the same as asked about
        # everything: an empty list means the caller had no ids, and answering
        # with the whole table would be a page of somebody else's numbers.
        rows = rows.filter(query) if (session_names or account_ids) else rows.none()

    per_account: dict[str, dict[str, Any]] = {}
    wanted = list(rows.values("id", "session_name", "phone", "status", "last_error", "display_name", "created_at"))
    joined = {
        row["account_id"]: row["n"]
        for row in (
            WorkerMembership.objects.filter(account_id__in=[r["id"] for r in wanted], status=WorkerMembership.Status.JOINED)
            .values("account_id")
            .annotate(n=models.Count("id"))
        )
    }
    for row in wanted:
        per_account[row["session_name"]] = {
            "account_id": row["id"],
            "phone": row["phone"],
            "worker_status": row["status"],
            "last_error": row["last_error"],
            "display_name": row["display_name"],
            "joined": joined.get(row["id"], 0),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    result: dict[str, Any] = {"per_account": per_account}
    if include_aggregate:
        counts = {row["status"]: row["n"] for row in WorkerAccount.objects.values("status").annotate(n=models.Count("id"))}
        result["aggregate"] = {
            "total": sum(counts.values()),
            "active": counts.get(WorkerAccount.Status.ACTIVE, 0),
            "disabled": counts.get(WorkerAccount.Status.DISABLED, 0),
            "error": counts.get(WorkerAccount.Status.ERROR, 0),
            "total_joined": WorkerMembership.objects.filter(status=WorkerMembership.Status.JOINED).count(),
        }
    return result


def delete_worker_account(
    *, account_id: Optional[int] = None, session_name: Optional[str] = None, phone: Optional[str] = None
) -> dict[str, Any]:
    """Remove the account rows the panel no longer trusts.

    Idempotent on purpose: a row that is already gone answers ``deleted: 0`` and
    HTTP 200, never a 404.  The panel calls this while deleting its own record,
    and a retry after a half-finished delete must not look like a new failure.

    The most specific key wins, because ``phone`` can match several rows —
    :func:`save_account` keeps one row per phone, but an older worker did not,
    and the caller asking by phone is the caller that does not know which.
    """
    close_old_connections()
    if account_id is not None:
        rows = WorkerAccount.objects.filter(id=account_id)
    elif session_name:
        rows = WorkerAccount.objects.filter(session_name=session_name)
    elif phone:
        rows = WorkerAccount.objects.filter(phone=phone)
    else:
        raise WorkerServiceError("one of account_id, session_name or phone is required")

    # Read before the delete, so the answer names what actually went — the
    # panel writes this into its own log and cannot ask again afterwards.
    doomed = list(rows.values("id", "session_name", "phone"))
    deleted = 0
    if doomed:
        with transaction.atomic():
            # Credential, throttle, health and memberships hang off the account
            # with ON DELETE CASCADE; the session string goes with them, which is
            # the half that actually matters.
            deleted, _ = WorkerAccount.objects.filter(id__in=[row["id"] for row in doomed]).delete()
        log.info("deleted %d account rows (%s)", len(doomed), ", ".join(r["session_name"][:16] for r in doomed))
    return {
        "deleted": len(doomed),
        "rows_removed": deleted,
        "sessions": [row["session_name"] for row in doomed],
        "phones": sorted({row["phone"] for row in doomed}),
    }


__all__ = [
    "StartAuthOutcome",
    "VerifyOutcome",
    "WorkerServiceError",
    "account_stats",
    "available_account_count",
    "build_session_name",
    "cancel_pending_login",
    "complete_phone_signup",
    "delete_worker_account",
    "normalize_display_name",
    "normalize_verification_code",
    "save_account",
    "start_phone_login",
    "verify_phone_code",
]
