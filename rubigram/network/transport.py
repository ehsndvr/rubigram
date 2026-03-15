from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from rubigram.exceptions import NetworkError, TransportError
from rubigram.network.headers import build_rpc_headers


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
        max_retries = max(0, self._pool.count - 1)

        for attempt in range(max_retries + 1):
            base_url = self._pool.get_current()
            try:
                response = await client.post(
                    base_url + "/",
                    content=body,
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as e:
                if attempt == max_retries:
                    raise NetworkError(
                        f"Request to {base_url} timed out after {max_retries + 1} attempts",
                        e,
                    ) from e
                self._pool.rotate()
            except httpx.ConnectError as e:
                if attempt == max_retries:
                    raise NetworkError(
                        f"Failed to connect to {base_url} after {max_retries + 1} attempts",
                        e,
                    ) from e
                self._pool.rotate()
            except httpx.RequestError as e:
                if attempt == max_retries:
                    raise NetworkError(
                        f"Request to {base_url} failed after {max_retries + 1} attempts",
                        e,
                    ) from e
                self._pool.rotate()
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    if attempt < max_retries:
                        self._pool.rotate()
                        continue
                raise TransportError(
                    f"HTTP error {e.response.status_code}: {e.response.text}"
                ) from e

        raise TransportError("Unexpected error in send_payload")

    async def fetch_dcs_plain(self) -> Dict[str, Any]:
        return await self._dc_discovery.fetch_dcs()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def __del__(self):
        if self._client is not None and hasattr(self._client, "close"):
            self._client.close()
