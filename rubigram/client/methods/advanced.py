"""The invoke seam and helpers shared by every mixin.

``Client.invoke`` is the single path from a :class:`~rubigram.raw.base.RawMethod`
to the wire:

- ``auth_mode == "auth"``  → encrypted envelope with the session auth
  (``api_version 6``, caesar ``auth``, RSA ``sign``) over the API (or bot) DC pool;
- ``auth_mode == "tmp"``   → encrypted with the temporary session (login flow);
- ``auth_mode == "none"``  → plain JSON (``getBaseInfo``, Rubino, web apps …).

Decrypted answers go through :func:`rubigram.errors.raise_for_status`, so
``client_show_message`` and the exact ``status_det`` classes are available.
``NOT_REGISTERED`` triggers one ``registerDevice`` + retry, like the web client.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TypeVar

from rubigram.client.base import BaseClient
from rubigram.enums import DcType
from rubigram.errors import AuthError, DecodeError, LoginRequired, NotRegistered, TransportError, is_ok, map_rpc_error
from rubigram.raw.base import RawMethod
from rubigram.raw.functions import build_data_object, build_plain_payload
from rubigram.raw.methods import SignIn, SignUp
from rubigram.types import RawObject
from rubigram.utils import generate_tmp_session

log = logging.getLogger(__name__)
ResultT = TypeVar("ResultT")
PeerLike = Any


class Advanced(BaseClient):
    """Low-level entry points and helpers (mixed into :class:`~rubigram.Client`)."""

    # -- public low level ------------------------------------------------

    async def invoke(self, method: RawMethod[ResultT], *, timeout: Optional[float] = None, retries: Optional[int] = None) -> ResultT:
        """Send a raw method and return its typed result.

        Raises :class:`~rubigram.errors.RpcError` subclasses for server
        errors, :class:`~rubigram.errors.NetworkError` for connectivity
        problems and :class:`~rubigram.errors.LoginRequired` when the method
        needs a session that does not exist.
        """
        if not isinstance(method, RawMethod):
            raise TypeError("invoke() expects a RawMethod instance")
        if self.is_bot:
            raise TransportError("Rubika RPC methods are not available on a bot-token session; use the Bot API methods")
        if method.auth_mode == "none":
            data = await self._call_service(method, timeout=timeout, retries=retries)
        else:
            data = await self._call_rpc(method, timeout=timeout, retries=retries, allow_register_retry=True)
        if method.unwrap_auth_on_success and isinstance(data, dict) and data.get("auth"):
            await self._finalize_login(data["auth"], data)
        return method.parse_response(self, data)

    async def invoke_raw(
        self,
        method_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        *,
        auth_mode: str = "auth",
        dc_type: DcType | str = DcType.API,
        api_version: Optional[str] = None,
        service_url: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> RawObject:
        """Call any Rubika method by name and return a :class:`~rubigram.types.RawObject`.

        Useful for methods that have no typed wrapper yet; the payload is
        built exactly like a declared method with the same ``auth_mode``.
        """
        from rubigram.raw.methods import METHODS

        known = METHODS.get(method_name)
        namespace: Dict[str, Any] = {
            "method_name": method_name,
            "auth_mode": auth_mode,
            "dc_type": DcType(dc_type) if not isinstance(dc_type, DcType) else dc_type,
            "api_version": api_version if api_version is not None else (known.api_version if known else None),
            "result": None,
            "_input": dict(input_data or {}),
            "to_input": lambda self: dict(self._input),
        }
        if service_url or (known is not None and getattr(known, "service_url", None)):
            namespace["service_url"] = service_url or getattr(known, "service_url", None)
        dynamic = type("DynamicRawMethod", (RawMethod,), namespace)
        return await self.invoke(dynamic(), timeout=timeout, retries=retries)  # type: ignore[abstract]

    # -- the seam --------------------------------------------------------

    async def _call_rpc(
        self, method: RawMethod[Any], *, timeout: Optional[float], retries: Optional[int], allow_register_retry: bool
    ) -> Any:
        if not self.is_connected or self._codec is None or self._http is None:
            raise AuthError("Client not started. Call start() first.")
        request_key = await self._resolve_request_key(method)
        if method.auth_mode == "auth" and method.name != "registerDevice":
            await self._ensure_registered_device()
        if isinstance(method, (SignIn, SignUp)) and method.public_key is None:
            public_key = await self.storage.public_key()
            if not public_key:
                raise AuthError("Public key is missing for the login flow")
            method.public_key = public_key

        data_object = build_data_object(method.name, method.to_input(), self.client_info)
        api_version = method.api_version or await self.storage.api_version()
        if method.auth_mode == "tmp":
            payload = self._codec.build_tmp_payload(api_version=api_version, tmp_session=request_key, data_obj=data_object)
        else:
            payload = self._codec.build_payload(api_version=api_version, auth=request_key, data_obj=data_object)

        transport = self._transport_for(method.dc_type)
        effective_retries = retries if retries is not None else method.retries
        response = await transport.send(payload, timeout=timeout, retries=effective_retries)
        if not is_ok(response):
            raise map_rpc_error(str(response.get("status")), response.get("status_det"), response, method=method.name)
        if "data_enc" not in response:
            raise DecodeError(f"Response of {method.name} has no data_enc: {response}")
        try:
            decrypted = self._codec.decrypt_response(response, request_key)
        except Exception as exc:
            raise DecodeError(f"Failed to decrypt the response of {method.name}: {exc}") from exc
        if not is_ok(decrypted):
            error = map_rpc_error(str(decrypted.get("status")), decrypted.get("status_det"), decrypted, method=method.name)
            if isinstance(error, NotRegistered) and allow_register_retry and method.name != "registerDevice" and method.auth_mode == "auth":
                log.info("%s answered NOT_REGISTERED; registering the device and retrying", method.name)
                await self.register_device(force=True)
                return await self._call_rpc(method, timeout=timeout, retries=retries, allow_register_retry=False)
            raise error
        await self.storage.set_api_url(transport.pool.get_current())
        return decrypted.get("data", decrypted) if isinstance(decrypted, dict) else decrypted

    async def _call_service(self, method: RawMethod[Any], *, timeout: Optional[float], retries: Optional[int]) -> Any:
        if not self.is_connected or self._service is None:
            raise AuthError("Client not started. Call start() first.")
        auth = await self.storage.auth()
        api_version = method.api_version or "0"
        client_info = (
            self.service_client_info
            if method.dc_type in (DcType.RUBINO, DcType.WALLET) or getattr(type(method), "service_url", None)
            else self.client_info
        )
        payload = build_plain_payload(method.name, method.to_input(), api_version=api_version, client_info=client_info, auth=auth)
        url = getattr(type(method), "service_url", None)
        if url is None:
            pool = self.dc.pool(method.dc_type)
            if pool.count == 0:
                raise TransportError(f"No {method.dc_type.value} DC URL is known; call get_base_info() first")
            url = pool.get_current().rstrip("/") + "/"
        effective_retries = retries if retries is not None else method.retries
        response = await self._service.send(payload, url=url, timeout=timeout, retries=effective_retries)
        if not is_ok(response):
            raise map_rpc_error(str(response.get("status")), response.get("status_det"), response, method=method.name)
        return response.get("data", response)

    def _transport_for(self, dc_type: DcType) -> Any:
        if dc_type is DcType.BOT and self._bot_dc_http is not None:
            return self._bot_dc_http
        assert self._http is not None
        return self._http

    async def _resolve_request_key(self, method: RawMethod[Any]) -> str:
        if method.auth_mode == "tmp":
            tmp_session = await self.storage.tmp_session()
            if not tmp_session:
                tmp_session = generate_tmp_session()
                await self.storage.set_tmp_session(tmp_session)
            await self._ensure_login_key_pair()
            return tmp_session
        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("This method requires an authenticated session")
        return auth


__all__ = ["Advanced"]
