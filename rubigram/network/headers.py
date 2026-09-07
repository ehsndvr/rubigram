"""Browser header profiles.

web.rubika.ir sets only ``Content-Type`` itself; Chrome adds the user agent,
origin, referer, ``sec-fetch-*`` and the ``sec-ch-ua*`` client hints.  The
functions below reproduce the full on-wire set for a configurable Chrome user
agent so requests from rubigram look like the real web client.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

WEB_ORIGIN = "https://web.rubika.ir"
WEB_REFERER = "https://web.rubika.ir/"
CHROME_MAJOR = "145"
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/{CHROME_MAJOR}.0.0.0 Safari/537.36"
)

BASE_BROWSER_HEADERS: Dict[str, str] = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,fa;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
}

_MAJOR_RE = re.compile(r"Chrome/(\d+)")


def _platform_from_user_agent(user_agent: str) -> str:
    if "Windows" in user_agent:
        return "Windows"
    if "Mac OS X" in user_agent or "Macintosh" in user_agent:
        return "macOS"
    if "Android" in user_agent:
        return "Android"
    if "Linux" in user_agent or "X11" in user_agent:
        return "Linux"
    return "Windows"


def build_client_hints(user_agent: Optional[str] = None) -> Dict[str, str]:
    """``sec-ch-ua*`` headers matching the Chrome major version of ``user_agent``."""
    agent = user_agent or CHROME_USER_AGENT
    match = _MAJOR_RE.search(agent)
    major = match.group(1) if match else CHROME_MAJOR
    return {
        "sec-ch-ua": f'"Google Chrome";v="{major}", "Chromium";v="{major}", "Not-A.Brand";v="24"',
        "sec-ch-ua-mobile": "?1" if "Android" in agent else "?0",
        "sec-ch-ua-platform": f'"{_platform_from_user_agent(agent)}"',
    }


def _browser_headers(user_agent: Optional[str]) -> Dict[str, str]:
    headers = dict(BASE_BROWSER_HEADERS)
    headers["user-agent"] = user_agent or CHROME_USER_AGENT
    headers.update(build_client_hints(user_agent))
    headers.update(
        {
            "origin": WEB_ORIGIN,
            "referer": WEB_REFERER,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
        }
    )
    return headers


def build_rpc_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    """Headers of an encrypted RPC request (``Content-Type: text/plain``)."""
    headers = _browser_headers(user_agent)
    headers["content-type"] = "text/plain"
    return headers


def build_json_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    """Headers of a plain-JSON request (``getDCs``, ``getBaseInfo``, Rubino, wallet)."""
    headers = _browser_headers(user_agent)
    headers["content-type"] = "application/json"
    return headers


def build_discovery_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    """Alias of :func:`build_json_headers` kept for older imports."""
    return build_json_headers(user_agent)


def build_websocket_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    """Extra headers sent with the WebSocket upgrade."""
    headers = {
        "accept-encoding": BASE_BROWSER_HEADERS["accept-encoding"],
        "accept-language": BASE_BROWSER_HEADERS["accept-language"],
        "cache-control": BASE_BROWSER_HEADERS["cache-control"],
        "pragma": BASE_BROWSER_HEADERS["pragma"],
    }
    headers.update(build_client_hints(user_agent))
    return headers


def build_upload_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    headers = _browser_headers(user_agent)
    headers["connection"] = "keep-alive"
    return headers


def build_download_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    headers = _browser_headers(user_agent)
    headers["content-type"] = "text/plain"
    headers["connection"] = "keep-alive"
    return headers


__all__ = [
    "WEB_ORIGIN",
    "WEB_REFERER",
    "CHROME_USER_AGENT",
    "BASE_BROWSER_HEADERS",
    "build_client_hints",
    "build_rpc_headers",
    "build_json_headers",
    "build_discovery_headers",
    "build_websocket_headers",
    "build_upload_headers",
    "build_download_headers",
]
