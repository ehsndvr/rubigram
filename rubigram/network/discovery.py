from __future__ import annotations

import contextlib
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from rubigram.enums import DcType
from rubigram.exceptions import NetworkError, TransportError
from rubigram.network.headers import build_discovery_headers


class DcDiscovery:
    """
    Handles discovery of Rubika's DC (Data Center) configuration.
    
    Rubika provides a list of available DCs via a separate endpoint.
    This class handles fetching and parsing that configuration.
    """
    
    DC_DISCOVERY_URL = "https://getdcmess.iranlms.ir/"
    BASE_INFO_URL = "https://servicesbase.iranlms.ir/"
    DEFAULT_URL_KEYS = {
        DcType.API: "default_api_urls",
        DcType.SOCKET: "default_sockets",
    }
    SUGGESTED_URL_KEYS = {
        DcType.API: "suggested_services",
        DcType.RUBINO: "suggested_rubino",
        DcType.WALLET: "suggested_payment",
    }
    
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

    async def fetch_base_info(self, auth: str, client_info: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "method": "getBaseInfo",
            "api_version": "0",
            "data": {},
            "auth": auth,
            "client": client_info,
        }

        try:
            response = await client.post(
                self.BASE_INFO_URL,
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise NetworkError(f"Failed to fetch base info: {e}", e)
        except Exception as e:
            raise TransportError(f"Failed to parse base info: {e}") from e

    @classmethod
    def urls_for(cls, payload: Dict[str, Any], dc_type: DcType | str) -> list[str]:
        normalized_type = cls._normalize_dc_type(dc_type)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        urls: list[str] = []

        key = cls.DEFAULT_URL_KEYS.get(normalized_type)
        if key is not None:
            cls._collect_urls(data.get(key), urls)
            return urls

        cls._collect_storage_urls(data.get("storages"), normalized_type, urls)
        return urls

    @classmethod
    def suggested_urls_for(cls, payload: Dict[str, Any], dc_type: DcType | str) -> list[str]:
        normalized_type = cls._normalize_dc_type(dc_type)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        suggested = data.get("suggested_urls", {})
        key = cls.SUGGESTED_URL_KEYS.get(normalized_type)
        urls: list[str] = []
        if key is None:
            return urls
        cls._collect_urls(suggested.get(key), urls)
        return urls

    @staticmethod
    def _normalize_dc_type(dc_type: DcType | str) -> DcType:
        if isinstance(dc_type, DcType):
            return dc_type
        return DcType(str(dc_type).strip().lower())

    @classmethod
    def _collect_storage_urls(cls, value: Any, dc_type: DcType, output: list[str], *, matched: bool = False) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                cls._collect_storage_urls(
                    item,
                    dc_type,
                    output,
                    matched=matched or str(key).strip().lower() == dc_type.value,
                )
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                cls._collect_storage_urls(item, dc_type, output, matched=matched)
            return
        if not isinstance(value, str):
            return

        if matched:
            cls._append_url(value, output)
            return

        host = urlparse(value).netloc or urlparse(f"https://{value}").netloc
        if host.startswith(dc_type.value) and host.endswith(".iranlms.ir"):
            cls._append_url(value, output)

    @classmethod
    def _collect_urls(cls, value: Any, output: list[str]) -> None:
        if isinstance(value, dict):
            for item in value.values():
                cls._collect_urls(item, output)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                cls._collect_urls(item, output)
            return
        if isinstance(value, str):
            cls._append_url(value, output)

    @staticmethod
    def _append_url(value: str, output: list[str]) -> None:
        normalized = value.strip()
        if not normalized:
            return
        host = urlparse(normalized).netloc or urlparse(f"https://{normalized}").netloc
        if not host:
            return
        url = f"https://{host}"
        if url not in output:
            output.append(url)
    
    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    def __del__(self):
        client = self._client
        if client is not None:
            with contextlib.suppress(Exception):
                client._transport.close()
