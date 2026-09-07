"""Request envelopes exactly as web.rubika.ir 4.4.34 builds them."""

from __future__ import annotations

from typing import Any, Dict, Optional

APP_NAME = "Main"
APP_VERSION = "4.4.34"
PACKAGE = "web.rubika.ir"
PLATFORM_WEB = "Web"
PLATFORM_PWA = "PWA"
LANG_CODE = "fa"
VERSION_PREFIX = "WB_"


def build_web_client_info(*, app_version: str = APP_VERSION, lang_code: str = LANG_CODE, platform: str = PLATFORM_WEB, package: str = PACKAGE, app_name: str = APP_NAME) -> Dict[str, str]:
    """The ``client`` object of encrypted RPCs (``getResponsePost``)."""
    return {
        "app_name": app_name,
        "app_version": app_version,
        "platform": platform,
        "package": package,
        "lang_code": lang_code,
    }


def build_service_client_info(*, app_version: str = APP_VERSION, package: str = PACKAGE, app_name: str = APP_NAME) -> Dict[str, str]:
    """The ``client`` object of service calls (Rubino, wallet, base info): platform PWA, no lang_code."""
    return {
        "app_name": app_name,
        "app_version": app_version,
        "platform": PLATFORM_PWA,
        "package": package,
    }


def build_data_object(method: str, input_data: Optional[Dict[str, Any]], client_info: Dict[str, str]) -> Dict[str, Any]:
    """The object that gets encrypted into ``data_enc``."""
    return {"method": method, "input": input_data or {}, "client": client_info}


def build_plain_payload(method: str, data: Optional[Dict[str, Any]], *, api_version: str, client_info: Dict[str, str], auth: Optional[str] = None) -> Dict[str, Any]:
    """Unencrypted payload (``not_encrypt`` calls and service calls)."""
    payload: Dict[str, Any] = {
        "method": method,
        "api_version": api_version,
        "data": data or {},
        "client": client_info,
    }
    if auth:
        payload["auth"] = auth
    return payload


__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "PACKAGE",
    "PLATFORM_WEB",
    "PLATFORM_PWA",
    "LANG_CODE",
    "VERSION_PREFIX",
    "build_web_client_info",
    "build_service_client_info",
    "build_data_object",
    "build_plain_payload",
]
