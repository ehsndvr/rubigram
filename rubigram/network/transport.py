from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from rubigram.enums import DcType
from rubigram.exceptions import NetworkError, TransportError
from rubigram.network.headers import build_discovery_headers, build_rpc_headers


class ApiUrlPool:
    """
    Manages a pool of API URLs for failover.
    
    This class handles:
    - Rotating through available URLs
    - Tracking the current index
    - Providing failover on network errors
    """
    
    def __init__(self, urls: List[str]):
        self._urls = urls
        self._current_index = 0
        self._lock = False  # Simple lock to prevent concurrent rotation
    
    @property
    def urls(self) -> List[str]:
        return self._urls
    
    @property
    def count(self) -> int:
        return len(self._urls)
    
    def get_current(self) -> str:
        """Get the current API URL."""
        if not self._urls:
            raise TransportError("No URLs available in the pool")
        return self._urls[self._current_index]
    
    def rotate(self) -> str:
        """
        Rotate to the next URL and return it.
        
        :return: The new current URL
        """
        if not self._urls:
            raise TransportError("No URLs available in the pool")
        
        self._current_index = (self._current_index + 1) % len(self._urls)
        return self._urls[self._current_index]
    
    def reset(self) -> None:
        """Reset the pool to the first URL."""
        if self._urls:
            self._current_index = 0
    
    def has_url(self, url: str) -> bool:
        """Check if a URL exists in the pool."""
        return url in self._urls

    def replace(self, urls: List[str]) -> None:
        """Replace pool URLs while preserving the current URL when possible."""
        deduped: List[str] = []
        for url in urls:
            if url and url not in deduped:
                deduped.append(url)

        if not deduped:
            raise TransportError("No URLs available in the pool")

        current = self.get_current() if self._urls else None
        self._urls = deduped
        if current and current in deduped:
            self._current_index = deduped.index(current)
        else:
            self._current_index = 0


class RpcTransport:
    """
    HTTP transport layer for Rubika API requests.
    
    Handles:
    - Sending encrypted payloads with correct headers
    - Failover between DCs
    - Error handling and retry logic
    """

    DEFAULT_TIMEOUT = 20.0

    def __init__(
        self,
        dc_discovery: "DcDiscovery",
        pool: ApiUrlPool,
        timeout: float = DEFAULT_TIMEOUT,
        pem_private_key: Optional[str] = None,
    ):
        self._dc_discovery = dc_discovery
        self._pool = pool
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=build_rpc_headers(),
            )
        return self._client

    async def send_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an encrypted payload to the current DC.

        :param payload: The encrypted payload dict
        :return: Parsed JSON response
        :raises NetworkError: If the request fails
        """
        client = await self._get_client()
        body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
        last_error: Exception | None = None

        for refresh_attempt in range(2):
            attempt_count = max(1, self._pool.count)

            for attempt in range(attempt_count):
                base_url = self._pool.get_current()
                try:
                    response = await client.post(
                        base_url + "/",
                        content=body,
                    )
                    response.raise_for_status()
                    return response.json()
                except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
                    last_error = e
                    if attempt < attempt_count - 1:
                        self._pool.rotate()
                        continue
                except httpx.HTTPStatusError as e:
                    if e.response.status_code >= 500:
                        last_error = e
                        if attempt < attempt_count - 1:
                            self._pool.rotate()
                            continue
                    else:
                        raise TransportError(
                            f"HTTP error {e.response.status_code}: {e.response.text}"
                        ) from e

                break

            if refresh_attempt == 0 and await self._refresh_pool():
                continue
            break

        if isinstance(last_error, httpx.TimeoutException):
            raise NetworkError(
                f"Request to {self._pool.get_current()} timed out after trying available API URLs",
                last_error,
            ) from last_error
        if isinstance(last_error, (httpx.ConnectError, httpx.RequestError)):
            raise NetworkError(
                f"Request to {self._pool.get_current()} failed after trying available API URLs",
                last_error,
            ) from last_error
        if isinstance(last_error, httpx.HTTPStatusError):
            raise TransportError(
                f"HTTP error {last_error.response.status_code}: {last_error.response.text}"
            ) from last_error

        raise TransportError("Unexpected error in send_payload")

    async def _refresh_pool(self) -> bool:
        try:
            dc_response = await self._dc_discovery.fetch_dcs()
        except Exception:
            return False

        urls = self._dc_discovery.urls_for(dc_response, DcType.API)
        if not urls:
            return False

        current_urls = list(self._pool.urls)
        deduped: List[str] = []
        for url in urls:
            if url and url not in deduped:
                deduped.append(url)

        if not deduped or deduped == current_urls:
            return False

        self._pool.replace(deduped)
        return True

    async def fetch_dcs_plain(self) -> Dict[str, Any]:
        return await self._dc_discovery.fetch_dcs()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def __del__(self):
        if self._client is not None and hasattr(self._client, "close"):
            self._client.close()


class JsonTransport:
    """HTTP transport for plain JSON APIs hosted on Rubika DCs."""

    DEFAULT_TIMEOUT = 20.0

    def __init__(self, urls: List[str], timeout: float = DEFAULT_TIMEOUT):
        self._pool = ApiUrlPool(urls)
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=build_discovery_headers(),
            )
        return self._client

    async def send_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_client()
        last_error: Exception | None = None
        attempt_count = max(1, self._pool.count)

        for attempt in range(attempt_count):
            base_url = self._pool.get_current().rstrip("/")
            try:
                response = await client.post(
                    base_url + "/",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
                last_error = e
                if attempt < attempt_count - 1:
                    self._pool.rotate()
                    continue
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500 and attempt < attempt_count - 1:
                    self._pool.rotate()
                    continue
                raise TransportError(
                    f"HTTP error {e.response.status_code}: {e.response.text}"
                ) from e
            break

        if isinstance(last_error, httpx.TimeoutException):
            raise NetworkError(
                f"Request to {self._pool.get_current()} timed out after trying available API URLs",
                last_error,
            ) from last_error
        if isinstance(last_error, (httpx.ConnectError, httpx.RequestError)):
            raise NetworkError(
                f"Request to {self._pool.get_current()} failed after trying available API URLs",
                last_error,
            ) from last_error
        if isinstance(last_error, httpx.HTTPStatusError):
            raise TransportError(
                f"HTTP error {last_error.response.status_code}: {last_error.response.text}"
            ) from last_error

        raise TransportError("Unexpected error in send_json")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def __del__(self):
        if self._client is not None and hasattr(self._client, "close"):
            self._client.close()
