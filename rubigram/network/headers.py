from __future__ import annotations

from typing import Dict

WEB_ORIGIN = "https://web.rubika.ir"
WEB_REFERER = "https://web.rubika.ir/"
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)

BASE_BROWSER_HEADERS: Dict[str, str] = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,fa;q=0.8,tr;q=0.7",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "user-agent": CHROME_USER_AGENT,
}


def build_rpc_headers() -> Dict[str, str]:
    headers = dict(BASE_BROWSER_HEADERS)
    headers.update(
        {
            "content-type": "text/plain",
            "origin": WEB_ORIGIN,
            "referer": WEB_REFERER,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
        }
    )
    return headers


def build_discovery_headers() -> Dict[str, str]:
    headers = dict(BASE_BROWSER_HEADERS)
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


def build_websocket_headers() -> Dict[str, str]:
    return {
        "accept-encoding": BASE_BROWSER_HEADERS['accept-encoding'],
        "accept-language": BASE_BROWSER_HEADERS["accept-language"],
        "cache-control": BASE_BROWSER_HEADERS["cache-control"],
        "pragma": BASE_BROWSER_HEADERS["pragma"],
        "referer": WEB_REFERER,
    }


def build_upload_headers() -> Dict[str, str]:
    headers = dict(BASE_BROWSER_HEADERS)
    headers.update(
        {
            "accept": "application/json, text/plain, */*",
            "origin": WEB_ORIGIN,
            "referer": WEB_REFERER,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "connection": "keep-alive",
        }
    )
    return headers


def build_download_headers() -> Dict[str, str]:
    headers = dict(BASE_BROWSER_HEADERS)
    headers.update(
        {
            "accept": "application/json, text/plain, */*",
            "content-type": "text/plain",
            "origin": WEB_ORIGIN,
            "referer": WEB_REFERER,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "connection": "keep-alive",
        }
    )
    return headers
