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
from django.db import close_old_connections, transaction

from rubigram import Client, errors
from rubigram.utils import normalize_phone_number

from .models import AccountThrottle, WorkerAccount, WorkerAccountCredential
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


async def start_phone_login(*, username: str, phone: str) -> StartAuthOutcome:
    """``sendCode`` for ``phone`` with a fresh temporary session."""
    normalized_phone = normalize_phone_number(phone)
    if not normalized_phone:
        raise WorkerServiceError("شماره تلفن نامعتبر است")
    session_name = build_session_name(username)
    client = build_client(session_name, timeout=float(settings.WORKER_LOGIN_TIMEOUT_SECONDS))
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
    _PENDING[session_name] = {"client": client, "phone": normalized_phone, "username": username}
    log.info("start_login session=%s send_type=%s", session_name[:16], sent.send_type)
    return StartAuthOutcome(
        transaction_hash=str(sent.phone_code_hash),
        phone=normalized_phone,
        session_name=session_name,
        device_hash=worker_device_hash(),
        login_state={"login_state": login_state, "phone": normalized_phone, "username": username},
    )


async def _login_client(session_name: str, login_state: Optional[dict[str, Any]]) -> tuple[Client, dict[str, Any]]:
    pending = _PENDING.get(session_name)
    if pending is not None:
        return pending["client"], pending
    state = str((login_state or {}).get("login_state") or "")
    if not state:
        raise WorkerServiceError("نشست ورود منقضی شده است؛ شماره را دوباره وارد کنید")
    client = build_client(session_name, state, timeout=float(settings.WORKER_LOGIN_TIMEOUT_SECONDS))
    await client.start()
    pending = {
        "client": client,
        "phone": str((login_state or {}).get("phone") or ""),
        "username": str((login_state or {}).get("username") or ""),
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
    *, username: str, phone: str, transaction_hash: str, code: str, session_name: str, login_state: Optional[dict[str, Any]] = None
) -> VerifyOutcome:
    """``signIn``; stores the account on success, ``requires_signup`` when the phone has no account."""
    normalized_code = normalize_verification_code(code)
    if not normalized_code:
        raise WorkerServiceError("کد تایید را فقط با عدد وارد کنید")
    lock = _VERIFY_LOCKS.setdefault(session_name, asyncio.Lock())
    async with lock:
        client, pending = await _login_client(session_name, login_state)
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
    *, username: str, phone: str, transaction_hash: str, display_name: str, session_name: str, login_state: Optional[dict[str, Any]] = None
) -> VerifyOutcome:
    """``signUp`` for a phone without an account (unverified against the live server)."""
    name = normalize_display_name(display_name)
    if not name:
        raise WorkerServiceError("برای تکمیل ثبت‌نام، یک نام وارد کنید")
    client, pending = await _login_client(session_name, login_state)
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


__all__ = [
    "StartAuthOutcome",
    "VerifyOutcome",
    "WorkerServiceError",
    "available_account_count",
    "build_session_name",
    "cancel_pending_login",
    "complete_phone_signup",
    "normalize_display_name",
    "normalize_verification_code",
    "save_account",
    "start_phone_login",
    "verify_phone_code",
]
