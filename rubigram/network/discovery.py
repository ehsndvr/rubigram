"""DC discovery (``getDCs`` / ``getBaseInfo``) and the DC repository."""

from __future__ import annotations

import contextlib
import logging
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import httpx

from rubigram.enums import DcType
from rubigram.errors import NetworkError, TransportError
from rubigram.network.headers import build_json_headers
from rubigram.network.pool import UrlPool

log = logging.getLogger(__name__)

# Defaults taken from the web client's configuration (used before getDCs answers).
DEFAULT_API_URL = "https://messengerg2c1.iranlms.ir"
DEFAULT_SOCKET_URL = "wss://jsocket5.iranlms.ir:80"
DEFAULT_RUBINO_URL = "https://rubino1.iranlms.ir/"
DEFAULT_WALLET_URL = "https://wallet1.iranlms.ir/"
DC_DISCOVERY_URL = "https://getdcmess.iranlms.ir/"
BASE_INFO_URL = "https://servicesbase.iranlms.ir/"
SERVICES_URL = "https://services.iranlms.ir"
WEBAPP_URL = "https://webapp1.iranlms.ir"
BARCODE_URL = "https://barcode.iranlms.ir/"

DEFAULT_CLIENT_INFO = {
    "app_name": "Main",
    "app_version": "4.4.34",
    "platform": "Web",
    "package": "web.rubika.ir",
    "lang_code": "fa",
}


def normalize_url(value: str) -> Optional[str]:
    """Return ``https://host[:port]`` for a bare host or URL, ``None`` when empty."""
    normalized = (value or "").strip()
    if not normalized:
        return None
    parsed = urlparse(normalized if "://" in normalized else f"https://{normalized}")
    if not parsed.netloc:
        return None
    scheme = parsed.scheme if parsed.scheme in {"http", "https", "ws", "wss"} else "https"
    return f"{scheme}://{parsed.netloc}"


class DcDiscovery:
    """Fetches the DC configuration and the service base info over plain JSON."""

    DC_DISCOVERY_URL = DC_DISCOVERY_URL
    BASE_INFO_URL = BASE_INFO_URL
    DEFAULT_URL_KEYS = {
        DcType.API: "default_api_urls",
        DcType.SOCKET: "default_sockets",
        DcType.BOT: "default_bot_urls",
        DcType.RUBINO: "default_rubino_urls",
        DcType.WALLET: "default_wallet_urls",
    }
    SUGGESTED_URL_KEYS = {
        DcType.API: "suggested_services",
        DcType.RUBINO: "suggested_rubino",
        DcType.WALLET: "suggested_payment",
    }

    def __init__(
        self,
        timeout: float = 20.0,
        *,
        proxy: Optional[str] = None,
        client_info: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
    ):
        self._timeout = timeout
        self._proxy = proxy
        self._client_info = dict(client_info or DEFAULT_CLIENT_INFO)
        self._user_agent = user_agent
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=build_json_headers(self._user_agent),
                proxy=self._proxy,
            )
        return self._client

    async def _post_json(self, url: str, payload: Dict[str, Any], what: str) -> Dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Failed to fetch {what}: timeout", exc) from exc
        except httpx.HTTPStatusError as exc:
            raise TransportError(f"Failed to fetch {what}: HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise NetworkError(f"Failed to fetch {what}: {exc}", exc) from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise TransportError(f"Failed to parse {what}: {exc}") from exc
        if not isinstance(data, dict):
            raise TransportError(f"Unexpected {what} payload: {type(data).__name__}")
        return data

    async def fetch_dcs(self) -> Dict[str, Any]:
        """``getDCs`` (api_version 4): API URLs, sockets, per-DC storages and CDN URLs."""
        payload = {
            "api_version": "4",
            "method": "getDCs",
            "client": self._client_info,
        }
        return await self._post_json(self.DC_DISCOVERY_URL, payload, "DC configuration")

    async def fetch_base_info(self, auth: str, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """``getBaseInfo`` (api_version 0) on the services base; needs a plain ``auth``."""
        payload = {
            "method": "getBaseInfo",
            "api_version": "0",
            "data": {},
            "auth": auth,
            "client": client_info,
        }
        return await self._post_json(self.BASE_INFO_URL, payload, "base info")

    # -- static helpers (also used by DcRepository) ------------------------

    @classmethod
    def urls_for(cls, payload: Dict[str, Any], dc_type: "DcType | str") -> List[str]:
        normalized_type = cls._normalize_dc_type(dc_type)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        urls: List[str] = []
        key = cls.DEFAULT_URL_KEYS.get(normalized_type)
        if key is not None:
            cls._collect_urls(data.get(key), urls)
            return urls
        cls._collect_storage_urls(data.get("storages"), normalized_type, urls)
        return urls

    @classmethod
    def suggested_urls_for(cls, payload: Dict[str, Any], dc_type: "DcType | str") -> List[str]:
        normalized_type = cls._normalize_dc_type(dc_type)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        suggested = data.get("suggested_urls") or {}
        key = cls.SUGGESTED_URL_KEYS.get(normalized_type)
        urls: List[str] = []
        if key is None:
            return urls
        cls._collect_urls(suggested.get(key), urls)
        return urls

    @staticmethod
    def _normalize_dc_type(dc_type: "DcType | str") -> DcType:
        if isinstance(dc_type, DcType):
            return dc_type
        return DcType(str(dc_type).strip().lower())

    @classmethod
    def _collect_storage_urls(cls, value: Any, dc_type: DcType, output: List[str], *, matched: bool = False) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                cls._collect_storage_urls(item, dc_type, output, matched=matched or str(key).strip().lower() == dc_type.value)
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
    def _collect_urls(cls, value: Any, output: List[str]) -> None:
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
    def _append_url(value: str, output: List[str]) -> None:
        url = normalize_url(value)
        if url and url not in output:
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


class DcRepository:
    """The client's view of the DC configuration (``dcRepo`` in the web client).

    Holds the ``getDCs`` payload plus the ``suggested_urls`` from
    ``getBaseInfo`` and hands out one rotating :class:`UrlPool` per
    :class:`~rubigram.enums.DcType`.  The whole state serializes to a dict so
    the client can persist it in the session storage.
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None, suggested_urls: Optional[Dict[str, str]] = None):
        self._data: Dict[str, Any] = {
            "default_api_urls": [DEFAULT_API_URL],
            "default_sockets": [DEFAULT_SOCKET_URL],
            "default_bot_urls": [DEFAULT_API_URL],
            "default_rubino_urls": [DEFAULT_RUBINO_URL],
            "default_wallet_urls": [DEFAULT_WALLET_URL],
            "default_cdn_urls": {},
            "storages": {},
        }
        self._suggested: Dict[str, str] = {}
        self._pools: Dict[DcType, UrlPool] = {}
        if data:
            self.update_from_dcs(data)
        if suggested_urls:
            self.update_from_base_info({"suggested_urls": suggested_urls})

    # -- ingestion --------------------------------------------------------

    def update_from_dcs(self, payload: Dict[str, Any]) -> None:
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            return
        for key, value in data.items():
            if value in (None, [], {}):
                continue
            self._data[key] = value
        self._pools.clear()

    def update_from_base_info(self, payload: Dict[str, Any]) -> None:
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        suggested = data.get("suggested_urls") if isinstance(data, dict) else None
        if not isinstance(suggested, dict):
            return
        self._suggested = {str(key): str(value) for key, value in suggested.items() if value}
        rubino = normalize_url(self._suggested.get("suggested_rubino", ""))
        if rubino:
            self._data["default_rubino_urls"] = [rubino]
        wallet = normalize_url(self._suggested.get("suggested_payment", ""))
        if wallet:
            self._data["default_wallet_urls"] = [wallet]
        self._pools.clear()

    # -- lookups ----------------------------------------------------------

    _KEYS = {
        DcType.API: "default_api_urls",
        DcType.BOT: "default_bot_urls",
        DcType.SOCKET: "default_sockets",
        DcType.RUBINO: "default_rubino_urls",
        DcType.WALLET: "default_wallet_urls",
    }

    def urls(self, dc_type: "DcType | str") -> List[str]:
        normalized = DcDiscovery._normalize_dc_type(dc_type)
        if normalized is DcType.DCS:
            return [DC_DISCOVERY_URL]
        raw = self._data.get(self._KEYS.get(normalized, ""), [])
        urls: List[str] = []
        DcDiscovery._collect_urls(raw, urls)
        return urls

    def pool(self, dc_type: "DcType | str") -> UrlPool:
        normalized = DcDiscovery._normalize_dc_type(dc_type)
        pool = self._pools.get(normalized)
        if pool is None:
            pool = UrlPool(self.urls(normalized))
            self._pools[normalized] = pool
        return pool

    @property
    def api_urls(self) -> List[str]:
        return self.urls(DcType.API)

    @property
    def socket_urls(self) -> List[str]:
        return self.urls(DcType.SOCKET)

    @property
    def storages(self) -> Dict[str, str]:
        value = self._data.get("storages")
        return dict(value) if isinstance(value, dict) else {}

    @property
    def cdn_urls(self) -> Dict[str, List[str]]:
        value = self._data.get("default_cdn_urls")
        return {str(k): list(v) for k, v in value.items()} if isinstance(value, dict) else {}

    @property
    def suggested_urls(self) -> Dict[str, str]:
        return dict(self._suggested)

    def storage_url(self, dc_id: "str | int") -> Optional[str]:
        """Full ``GetFile.ashx`` URL of a DC, as used by the web client for downloads."""
        value = self.storages.get(str(dc_id))
        return str(value) if value else None

    def cdn_urls_for(self, tag: str) -> List[str]:
        return list(self.cdn_urls.get(str(tag), []))

    # -- persistence ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {"dcs": dict(self._data), "suggested_urls": dict(self._suggested)}

    @classmethod
    def from_dict(cls, value: Optional[Dict[str, Any]]) -> "DcRepository":
        if not isinstance(value, dict):
            return cls()
        return cls(value.get("dcs") or {}, value.get("suggested_urls") or {})

    def merge_urls(self, dc_type: "DcType | str", extra: Iterable[str]) -> None:
        """Append user-configured URLs (for example custom socket URLs)."""
        normalized = DcDiscovery._normalize_dc_type(dc_type)
        key = self._KEYS.get(normalized)
        if key is None:
            return
        current: List[str] = []
        DcDiscovery._collect_urls(self._data.get(key), current)
        for url in extra:
            normalized_url = normalize_url(url)
            if normalized_url and normalized_url not in current:
                current.append(normalized_url)
        self._data[key] = current
        self._pools.pop(normalized, None)


__all__ = [
    "DcDiscovery",
    "DcRepository",
    "normalize_url",
    "DEFAULT_API_URL",
    "DEFAULT_SOCKET_URL",
    "DEFAULT_RUBINO_URL",
    "DEFAULT_WALLET_URL",
    "DEFAULT_CLIENT_INFO",
    "DC_DISCOVERY_URL",
    "BASE_INFO_URL",
    "SERVICES_URL",
    "WEBAPP_URL",
    "BARCODE_URL",
]
