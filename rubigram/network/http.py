"""HTTPS transports: the encrypted RPC envelope and plain-JSON service calls.

Both transports share the web client's behaviour: a per-attempt timeout, the
``0, 2, 3, 5, 10`` second retry ladder, and rotation to the next DC URL before
every retry.  When every URL failed once, an optional ``refresh_urls``
coroutine (normally a fresh ``getDCs``) is consulted a single time.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

import httpx

from rubigram.errors import NetworkError, RequestTimeout, TransportError
from rubigram.network.headers import build_json_headers, build_rpc_headers
from rubigram.network.pool import UrlPool
from rubigram.network.retry import DEFAULT_RETRY_POLICY, RetryPolicy, run_with_retries

log = logging.getLogger(__name__)

RefreshUrls = Callable[[], Awaitable[Optional[List[str]]]]


@dataclass(frozen=True)
class HttpRequestRecord:
    """The last request a transport sent (useful for tests and debugging)."""

    url: str
    body: str
    headers: Dict[str, str]


class _RetryableFailure(Exception):
    """Internal marker: the attempt failed in a way the ladder may retry."""

    def __init__(self, error: Exception):
        super().__init__(str(error))
        self.error = error


class _BaseHttpTransport:
    def __init__(
        self,
        pool: "UrlPool | Iterable[str] | str",
        *,
        timeout: float = 20.0,
        proxy: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
        refresh_urls: Optional[RefreshUrls] = None,
        user_agent: Optional[str] = None,
    ):
        if isinstance(pool, UrlPool):
            self._pool = pool
        elif isinstance(pool, str):
            self._pool = UrlPool([pool])
        else:
            self._pool = UrlPool(list(pool))
        self._timeout = timeout
        self._proxy = proxy
        self._headers = headers if headers is not None else self._default_headers(user_agent)
        self._retry_policy = retry_policy.with_overrides(timeout=timeout)
        self._refresh_urls = refresh_urls
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request: Optional[HttpRequestRecord] = None

    def _default_headers(self, user_agent: Optional[str]) -> Dict[str, str]:  # pragma: no cover - overridden
        return build_rpc_headers(user_agent)

    @property
    def pool(self) -> UrlPool:
        return self._pool

    @property
    def last_request(self) -> Optional[HttpRequestRecord]:
        return self._last_request

    @property
    def retry_policy(self) -> RetryPolicy:
        return self._retry_policy

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, headers=self._headers, proxy=self._proxy)
        return self._client

    def use_client(self, client: httpx.AsyncClient) -> None:
        """Inject an ``httpx.AsyncClient`` (tests use ``httpx.MockTransport``)."""
        self._client = client

    async def _post_once(self, url: str, body: str, timeout: float, *, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        client = await self._get_client()
        headers = {**self._headers, **(extra_headers or {})}
        self._last_request = HttpRequestRecord(url=url, body=body, headers=headers)
        try:
            response = await client.post(url, content=body, headers=headers, timeout=timeout)
        except httpx.TimeoutException as exc:
            raise _RetryableFailure(RequestTimeout(f"Request to {url} timed out after {timeout:.0f}s", exc)) from exc
        except httpx.HTTPError as exc:
            raise _RetryableFailure(NetworkError(f"Request to {url} failed: {exc}", exc)) from exc
        if response.status_code >= 500:
            raise _RetryableFailure(TransportError(f"HTTP error {response.status_code} from {url}: {response.text[:200]}"))
        if response.status_code >= 400:
            raise TransportError(f"HTTP error {response.status_code} from {url}: {response.text[:200]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise _RetryableFailure(TransportError(f"Invalid JSON from {url}: {exc}")) from exc
        if not isinstance(data, dict):
            raise TransportError(f"Unexpected response type from {url}: {type(data).__name__}")
        return data

    async def _send(self, body: str, *, timeout: Optional[float], retries: Optional[int], url: Optional[str] = None, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        policy = self._retry_policy.with_overrides(retries=retries, timeout=timeout)
        refreshed = False

        async def attempt(index: int) -> Dict[str, Any]:
            target = url if url else self._pool.get_current().rstrip("/") + "/"
            return await self._post_once(target, body, policy.timeout, extra_headers=extra_headers)

        async def on_retry(index: int, exc: BaseException) -> None:
            nonlocal refreshed
            if url is None:
                self._pool.force_rotate()
                if not refreshed and index + 1 >= self._pool.count and self._refresh_urls is not None:
                    refreshed = True
                    try:
                        urls = await self._refresh_urls()
                    except Exception as refresh_exc:  # noqa: BLE001 - discovery failures must not mask the request error
                        log.debug("URL refresh failed: %s", refresh_exc)
                        urls = None
                    if urls:
                        self._pool.replace(urls, strict=False)

        try:
            return await run_with_retries(
                policy,
                attempt,
                retryable=lambda exc: isinstance(exc, _RetryableFailure),
                on_retry=on_retry,
                label="rpc",
            )
        except _RetryableFailure as failure:
            raise failure.error from failure.error

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class HttpTransport(_BaseHttpTransport):
    """Sends the encrypted envelope (``text/plain`` JSON body) to the API DCs."""

    def _default_headers(self, user_agent: Optional[str]) -> Dict[str, str]:
        return build_rpc_headers(user_agent)

    async def send(self, payload: Dict[str, Any], *, timeout: Optional[float] = None, retries: Optional[int] = None) -> Dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        return await self._send(body, timeout=timeout, retries=retries)

    # Old name used by the previous implementation.
    async def send_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.send(payload)


class JsonTransport(_BaseHttpTransport):
    """Plain-JSON POST used by Rubino, wallet, web apps and service base calls."""

    def _default_headers(self, user_agent: Optional[str]) -> Dict[str, str]:
        return build_json_headers(user_agent)

    async def send(self, payload: Dict[str, Any], *, url: Optional[str] = None, timeout: Optional[float] = None, retries: Optional[int] = None) -> Dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        return await self._send(body, timeout=timeout, retries=retries, url=url)

    async def send_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.send(payload)


# Backward-compatible name.
RpcTransport = HttpTransport

__all__ = ["HttpTransport", "JsonTransport", "RpcTransport", "HttpRequestRecord"]
