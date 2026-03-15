from __future__ import annotations

import contextlib
from typing import Any, Dict, Optional

import httpx

from rubigram.exceptions import NetworkError, TransportError
from rubigram.network.headers import build_discovery_headers


class DcDiscovery:
    """
    Handles discovery of Rubika's DC (Data Center) configuration.
    
    Rubika provides a list of available DCs via a separate endpoint.
    This class handles fetching and parsing that configuration.
    """
    
    DC_DISCOVERY_URL = "https://getdcmess.iranlms.ir/"
    
    def __init__(self, timeout: float = 20.0):
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=build_discovery_headers(),
            )
        return self._client
    
    async def fetch_dcs(self) -> Dict[str, Any]:
        """
        Fetch the current DC configuration from Rubika.
        
        :return: Parsed DC configuration dict
        :raises NetworkError: If the request fails
        """
        client = await self._get_client()
        
        payload = {
            "api_version": "4",
            "method": "getDCs",
            "client": {
                "app_name": "Main",
                "app_version": "4.4.27",
                "platform": "Web",
                "package": "web.rubika.ir",
                "lang_code": "fa"
            }
        }
        
        try:
            response = await client.post(
                self.DC_DISCOVERY_URL,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to fetch DC configuration: {e}", e)
        except Exception as e:
            raise TransportError(f"Failed to parse DC configuration: {e}") from e
    
    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    def __del__(self):
        client = self._client
        if client is not None:
            with contextlib.suppress(Exception):
                client._transport.close()
