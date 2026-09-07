"""Login flow, device registration and logout."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Union

from rubigram.crypto import export_public_key_for_login, generate_rsa_key_pair
from rubigram.errors import AuthError, CodeIsExpired, CodeIsInvalid, CodeIsUsed, InvalidInput, LoginRequired, RpcError, RubigramError
from rubigram.raw.methods import GetTime, Logout, RegisterDevice, SendCode, SignIn, SignUp, UnregisterDevice
from rubigram.types import Authorization, Empty, SentCode, TimeResult
from rubigram.utils import device_hash_from_user_agent, generate_device_hash, normalize_phone_number

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client

log = logging.getLogger(__name__)
CodeCallback = Callable[..., Union[str, Awaitable[str]]]
_INNER_STATUS_ERRORS = {"CodeIsInvalid": CodeIsInvalid, "CodeIsExpired": CodeIsExpired, "CodeIsUsed": CodeIsUsed}


async def _prompt(text: str) -> str:
    """Interactive fallback used only when no ``code_callback`` is configured."""
    return await asyncio.to_thread(input, text)


class Auth:
    async def send_code(self: "Client", phone_number: str, *, send_type: str = "SMS", pass_key: Optional[str] = None) -> SentCode:
        """Ask Rubika to send a login code (``sendCode``). [HTTP]"""
        self._require_user_session("send_code")
        return await self.invoke(SendCode(phone_number=normalize_phone_number(phone_number), send_type=send_type, pass_key=pass_key))

    async def sign_in(self: "Client", phone_number: str, phone_code_hash: str, phone_code: str) -> Authorization:
        """Confirm the code (``signIn``); on success the session ``auth`` is stored. [HTTP]"""
        self._require_user_session("sign_in")
        authorization = await self.invoke(SignIn(phone_number=normalize_phone_number(phone_number), phone_code_hash=phone_code_hash, phone_code=str(phone_code).strip()))
        error = _INNER_STATUS_ERRORS.get(str(authorization.status or "OK"))
        if error is not None:
            raise error(str(authorization.status), None, authorization.to_dict(), method="signIn")
        return authorization

    async def sign_up(self: "Client", first_name: str, last_name: str = "") -> Authorization:
        """Register a new account (``signUp``); unverified against the current server. [HTTP]"""
        self._require_user_session("sign_up")
        return await self.invoke(SignUp(first_name=first_name, last_name=last_name))

    async def login(
        self: "Client",
        phone_number: Optional[str] = None,
        *,
        code: Optional[str] = None,
        code_callback: Optional[CodeCallback] = None,
        password: Optional[str] = None,
        max_attempts: int = 3,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Authorization:
        """Full phone login: ``sendCode`` → ``signIn`` (→ ``signUp`` for new accounts).

        The code comes from ``code``, else ``code_callback(sent_code)`` (sync or
        async), else the ``code_callback`` given to the constructor, else an
        interactive prompt.  Returns the :class:`~rubigram.types.Authorization`
        and stores the session.  [HTTP]
        """
        self._require_user_session("login")
        if await self.storage.auth():
            user_guid = await self.storage.user_guid()
            return Authorization(client=self, status="OK", user_guid=user_guid)
        phone = phone_number or self.phone_number
        callback = code_callback or self.code_callback
        if not phone:
            if callback is None and not self.interactive:
                raise LoginRequired("No session: pass phone_number= or a code_callback= to log in")
            phone = await _prompt("Enter phone number (international format, e.g. 989121234567): ")
        self.phone_number = normalize_phone_number(phone)
        sent = await self.send_code(self.phone_number)
        if sent.status == "SendPassKey":
            if not password:
                if not self.interactive:
                    raise AuthError("Two-step verification is enabled; pass password= to login()")
                password = await _prompt(f"Enter the two-step password (hint: {sent.hint or '-'}): ")
            sent = await self.send_code(self.phone_number, pass_key=password)
        if not sent.phone_code_hash:
            raise AuthError(f"sendCode did not return phone_code_hash (status {sent.status})")
        last_error: Optional[RpcError] = None
        for attempt in range(max(1, max_attempts)):
            value = code if attempt == 0 and code else (self.phone_code if attempt == 0 and self.phone_code else await self._resolve_code(sent, callback))
            try:
                authorization = await self.sign_in(self.phone_number, sent.phone_code_hash, str(value))
            except (CodeIsInvalid, CodeIsExpired, InvalidInput) as exc:
                last_error = exc
                log.warning("Sign-in attempt %d failed: %s", attempt + 1, exc)
                if attempt + 1 >= max_attempts or (code and attempt == 0 and callback is None and not self.interactive):
                    raise
                continue
            if await self.storage.auth():
                return authorization
            name = first_name or self.first_name
            if not name:
                if not self.interactive:
                    raise AuthError("The account is not registered; pass first_name= to sign up")
                name = await _prompt("Enter first name: ")
            return await self.sign_up(name, last_name if last_name is not None else self.last_name)
        assert last_error is not None
        raise last_error

    async def _resolve_code(self: "Client", sent: SentCode, callback: Optional[CodeCallback]) -> str:
        if callback is None:
            if not self.interactive:
                raise LoginRequired("A verification code is required; pass code= or code_callback=")
            return await _prompt(f"Enter the confirmation code sent via {sent.send_type or 'SMS'}: ")
        result = callback(sent)
        if inspect.isawaitable(result):
            result = await result
        return str(result).strip()

    async def authorize(self: "Client") -> Any:
        """rubigram 0.1 name of :meth:`login` (bots just persist their token)."""
        if self.is_bot:
            await self.storage.set_bot_token(self.token)
            return {"bot_token": self.token}
        return await self.login()

    async def register_device(self: "Client", force: bool = False) -> Empty:
        """``registerDevice`` with the web-client payload; skipped when already registered for this app version. [HTTP]"""
        self._require_user_session("register_device")
        if not self.enable_register_device:
            return Empty(client=self)
        if not await self.storage.auth():
            raise LoginRequired("registerDevice requires an authenticated session")
        if not force and await self.storage.registered_device() and await self.storage.registered_device_version() == self.app_version:
            return Empty(client=self)
        async with self._register_lock:
            await self.storage.set_registered_device(False)
            await self.storage.set_registered_device_version(None)
            device_hash = await self._ensure_device_hash()
            method = RegisterDevice(
                token_type=self.REGISTER_DEVICE_TOKEN_TYPE,
                token="",
                app_version=f"{self.REGISTER_DEVICE_APP_VERSION_PREFIX}{self.app_version}",
                lang_code=self.lang_code,
                system_version=self.system_version,
                device_model=self.device_model,
                device_hash=device_hash,
            )
            data = await self._call_rpc(method, timeout=None, retries=None, allow_register_retry=False)
            await self.storage.set_registered_device(True)
            await self.storage.set_registered_device_version(self.app_version)
            return method.parse_response(self, data)

    async def unregister_device(self: "Client", device: Optional[dict[str, Any]] = None) -> Empty:
        """``unregisterDevice`` (sent unencrypted like the web client). [HTTP]"""
        self._require_user_session("unregister_device")
        result = await self.invoke(UnregisterDevice(device=device))
        await self.storage.set_registered_device(False)
        return result

    async def logout(self: "Client") -> Empty:
        """``logout`` and forget the stored auth. [HTTP]"""
        self._require_user_session("logout")
        try:
            result = await self.invoke(Logout())
        finally:
            await self.storage.clear_auth()
            if self._socket is not None:
                await self._socket.close()
                self._socket = None
        return result

    async def get_time(self: "Client") -> TimeResult:
        """Server time (``getTime``). [HTTP]"""
        return await self.invoke(GetTime())

    # -- internals ---------------------------------------------------------

    async def _finalize_login(self: "Client", encrypted_auth: str, data: dict[str, Any]) -> None:
        assert self._codec is not None
        try:
            auth = self._codec.unwrap_server_auth(encrypted_auth)
        except Exception as exc:  # noqa: BLE001
            raise AuthError(f"Failed to unwrap the server auth: {exc}") from exc
        await self.storage.set_auth(auth)
        await self.storage.set_tmp_session(None)
        await self.storage.set_registered_device(False)
        await self.storage.set_registered_device_version(None)
        user_guid = data.get("user_guid")
        if not user_guid and isinstance(data.get("user"), dict):
            user_guid = data["user"].get("user_guid")
        if user_guid:
            await self.storage.set_user_guid(user_guid)
            self._cached_user_guid = user_guid
        self.session_invalid = False
        try:
            await self.register_device(force=True)
        except RubigramError as exc:
            log.warning("registerDevice failed right after login: %s", exc)
        if self._transport_mode.is_ws and self.enable_socket:
            try:
                await self._ensure_socket(force_reconnect=True)
            except RubigramError as exc:
                log.warning("Socket connection failed right after login: %s", exc)
        await self._ensure_listener()

    async def _ensure_login_key_pair(self: "Client") -> None:
        public_key = await self.storage.public_key()
        private_key_pem = await self.storage.private_key_pem()
        if private_key_pem:
            expected = export_public_key_for_login(private_key_pem)
            if public_key != expected:
                await self.storage.set_public_key(expected)
            return
        if self.pem_private_key:
            private_key_pem = self.pem_private_key
            public_key = export_public_key_for_login(private_key_pem)
        else:
            public_key, private_key_pem = generate_rsa_key_pair()
        await self.storage.set_public_key(public_key)
        await self.storage.set_private_key_pem(private_key_pem)

    async def _ensure_registered_device(self: "Client", force: bool = False) -> None:
        if not self.enable_register_device or not await self.storage.auth():
            return
        if not force and await self.storage.registered_device() and await self.storage.registered_device_version() == self.app_version:
            return
        await self.register_device(force=True)

    async def _ensure_device_hash(self: "Client") -> str:
        stored = await self.storage.device_hash()
        device_hash = self.device_hash or stored
        if not device_hash:
            device_hash = device_hash_from_user_agent(self.user_agent) if self.user_agent else generate_device_hash()
        if device_hash != stored:
            await self.storage.set_device_hash(device_hash)
        self.device_hash = device_hash
        return device_hash


__all__ = ["Auth", "CodeCallback"]
