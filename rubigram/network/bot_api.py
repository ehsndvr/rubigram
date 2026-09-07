"""HTTP transport for the Rubika Bot API (``https://botapi.rubika.ir/v3/{token}/{method}``)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import httpx

from rubigram.errors import BotApiError, NetworkError, RequestTimeout, TransportError, map_rpc_error
from rubigram.network.retry import DEFAULT_RETRY_POLICY, RetryPolicy, run_with_retries

log = logging.getLogger(__name__)


class _Retry(Exception):
    def __init__(self, error: Exception):
        super().__init__(str(error))
        self.error = error


class BotTransport:
    """Sends Bot API calls and uploads/downloads bot files."""

    DEFAULT_BASE_URL = "https://botapi.rubika.ir/v3"
    DEFAULT_TIMEOUT = 20.0

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        proxy: Optional[str] = None,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    ):
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._proxy = proxy
        self._retry_policy = retry_policy.with_overrides(timeout=timeout)
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request: Optional[tuple[str, Dict[str, Any]]] = None

    @property
    def token(self) -> str:
        return self._token

    @property
    def last_request(self) -> Optional[tuple[str, Dict[str, Any]]]:
        return self._last_request

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, proxy=self._proxy)
        return self._client

    def use_client(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def build_method_url(self, method: str) -> str:
        return f"{self._base_url}/{self._token}/{method}"

    _build_method_url = build_method_url

    async def call_method(
        self, method: str, payload: Optional[Dict[str, Any]] = None, *, timeout: Optional[float] = None, retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """POST ``payload`` and return the raw JSON answer (``{"status": …, "data": …}``)."""
        client = await self._get_client()
        policy = self._retry_policy.with_overrides(retries=retries, timeout=timeout)
        body = payload or {}
        url = self.build_method_url(method)
        self._last_request = (method, dict(body))

        async def attempt(index: int) -> Dict[str, Any]:
            try:
                response = await client.post(url, json=body, timeout=policy.timeout)
            except httpx.TimeoutException as exc:
                raise _Retry(RequestTimeout(f"Bot API request {method} timed out", exc)) from exc
            except httpx.HTTPError as exc:
                raise _Retry(NetworkError(f"Bot API request failed for {method}: {exc}", exc)) from exc
            if response.status_code >= 500:
                raise _Retry(TransportError(f"Bot API HTTP {response.status_code}: {response.text[:200]}"))
            if response.status_code >= 400:
                raise TransportError(f"Bot API HTTP {response.status_code}: {response.text[:200]}")
            try:
                data = response.json()
            except ValueError as exc:
                raise TransportError(f"Bot API returned invalid JSON for {method}: {exc}") from exc
            if not isinstance(data, dict):
                raise TransportError(f"Bot API returned an unexpected payload for {method}")
            return data

        try:
            return await run_with_retries(policy, attempt, retryable=lambda exc: isinstance(exc, _Retry), label=f"bot {method}")
        except _Retry as failure:
            raise failure.error from failure.error

    async def call(
        self, method: str, payload: Optional[Dict[str, Any]] = None, *, timeout: Optional[float] = None, retries: Optional[int] = None
    ) -> Any:
        """Call a Bot API method and return its ``data`` / ``result`` part.

        Raises :class:`BotApiError` for ``ok: false`` answers and the mapped
        :class:`RpcError` for ``status != OK`` answers.
        """
        response = await self.call_method(method, payload, timeout=timeout, retries=retries)
        return self.unwrap(response, method=method)

    @staticmethod
    def unwrap(response: Any, *, method: Optional[str] = None) -> Any:
        if not isinstance(response, dict):
            return response
        if "ok" in response:
            if response.get("ok") is False:
                raise BotApiError(
                    str(response.get("description") or response.get("error") or "Bot API request failed"),
                    error_code=response.get("error_code"),
                    raw=response,
                )
            return response.get("result")
        status = response.get("status")
        if status and status != "OK":
            raise map_rpc_error(str(status), response.get("status_det"), response, method=method)
        if "data" in response:
            return response["data"]
        return response

    async def upload_file(
        self, upload_url: str, path: Union[str, Path], *, field_name: str = "file", file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Multipart upload to the URL returned by the bot ``requestSendFile``."""
        client = await self._get_client()
        file_path = Path(path)
        try:
            with file_path.open("rb") as stream:
                response = await client.post(
                    upload_url, files={field_name: (file_name or file_path.name, stream)}, timeout=max(self._timeout, 60.0)
                )
        except httpx.TimeoutException as exc:
            raise RequestTimeout("Bot file upload timed out", exc) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(f"Bot file upload failed: {exc}", exc) from exc
        if response.status_code >= 400:
            raise TransportError(f"Bot upload HTTP {response.status_code}: {response.text[:200]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise TransportError(f"Bot upload returned invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise TransportError("Bot upload returned an unexpected payload")
        return data

    async def download_file(self, url: str, *, path: Union[str, Path, None] = None, in_memory: bool = False) -> Union[bytes, Path]:
        """Download the ``download_url`` returned by the bot ``getFile``."""
        client = await self._get_client()
        try:
            response = await client.get(url, timeout=max(self._timeout, 60.0))
        except httpx.TimeoutException as exc:
            raise RequestTimeout("Bot file download timed out", exc) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(f"Bot file download failed: {exc}", exc) from exc
        if response.status_code >= 400:
            raise TransportError(f"Bot download HTTP {response.status_code}")
        if in_memory or path is None:
            return response.content
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)
        return output

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


BotApiTransport = BotTransport

__all__ = ["BotApiTransport", "BotTransport"]
