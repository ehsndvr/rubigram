from __future__ import annotations

from typing import Any, Optional

import httpx

from rubigram.exceptions import NetworkError, TransportError


class BotTransport:
    DEFAULT_BASE_URL = "https://botapi.rubika.ir/v3"
    DEFAULT_TIMEOUT = 20.0

    def __init__(self, token: str, *, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    def _build_method_url(self, method: str) -> str:
        return f"{self._base_url}/{self._token}/{method}"

    async def call_method(self, method: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.post(self._build_method_url(method), json=payload or {})
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise NetworkError(f"Bot API request failed for {method}: {exc}", exc) from exc
        except httpx.HTTPStatusError as exc:
            raise TransportError(f"Bot API HTTP {exc.response.status_code}: {exc.response.text}") from exc

        try:
            return response.json()
        except Exception as exc:
            raise TransportError(f"Bot API returned invalid JSON for {method}: {exc}") from exc

    async def upload_file(self, upload_url: str, path: str, *, field_name: str = "file") -> dict[str, Any]:
        client = await self._get_client()
        try:
            with open(path, "rb") as stream:
                response = await client.post(upload_url, files={field_name: stream})
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise NetworkError(f"Bot file upload failed: {exc}", exc) from exc
        except httpx.HTTPStatusError as exc:
            raise TransportError(f"Bot upload HTTP {exc.response.status_code}: {exc.response.text}") from exc

        try:
            return response.json()
        except Exception as exc:
            raise TransportError(f"Bot upload returned invalid JSON: {exc}") from exc

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
