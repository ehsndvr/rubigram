"""Where a login leaves this machine from, and how to say so.

The panel picks an exit country per registration.  That choice used to move only
the panel's own hop: the connection Rubika actually sees is the one opened
*here*, from this worker, and until the payload carried a ``proxy`` the panel's
country was a label on a request that went out from the worker's own address.

Two things live here, and they are deliberately separate:

* :func:`normalize_requested_proxy` — the exit the caller asked for, checked
  rather than trusted.  A signature proves who sent the field, not that it is
  well formed, and a malformed proxy does not fail here: it fails several layers
  down inside the transport, as a connection error that reads like Rubika being
  unreachable.
* :func:`measure_egress` — the address the outside world *actually* sees through
  that proxy.  A promise is not a measurement, and this is the only way to answer
  the question the operator really has: did this number register from the address
  the panel chose?  It is best effort by construction — reporting where a login
  went out from must never be the reason it did not happen.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

import httpx
from django.conf import settings

log = logging.getLogger("membership_worker.exit")

PROXY_SCHEMES = ("http", "https", "socks5", "socks5h", "socks4")

# Long enough for an IPv6 address with a zone id, short enough that an echo
# service answering with an HTML error page is discarded rather than logged as
# an address.
_MAX_IP_LENGTH = 45


class InvalidProxyUrl(ValueError):
    """The caller asked for an exit that cannot be used."""


def normalize_requested_proxy(raw: object) -> Optional[str]:
    """Validate the proxy URL a caller asked this call to leave through."""
    if raw in (None, ""):
        return None
    if not isinstance(raw, str):
        raise InvalidProxyUrl("proxy must be a string")
    value = raw.strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in PROXY_SCHEMES:
        raise InvalidProxyUrl(f"unsupported proxy scheme: {parsed.scheme or '(none)'} (expected one of {', '.join(PROXY_SCHEMES)})")
    if not parsed.hostname:
        raise InvalidProxyUrl("proxy is missing a host")
    if parsed.port is None:
        raise InvalidProxyUrl("proxy is missing a port")
    return value


def describe_proxy(url: Optional[str]) -> str:
    """A proxy without its credentials — safe for a log line.  These carry a password."""
    if not url:
        return "direct"
    try:
        parsed = urlparse(url)
    except ValueError:
        return "?"
    host = parsed.hostname or "?"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme or '?'}://{host}{port}"


async def measure_egress(proxy: Optional[str]) -> Optional[str]:
    """The address the outside world sees for this proxy, or ``None`` if unknown.

    The echo service is ``WORKER_EGRESS_ECHO_URL`` — plain text, one address, no
    JSON to parse and no key to be renamed under us — and setting it empty turns
    the check off entirely.
    """
    url = str(settings.WORKER_EGRESS_ECHO_URL or "").strip()
    if not url:
        return None
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=float(settings.WORKER_EGRESS_TIMEOUT_SECONDS)) as client:
            ip = (await client.get(url)).text.strip()
            return ip if ip and len(ip) <= _MAX_IP_LENGTH else None
    except Exception as exc:
        log.warning("egress check failed for %s: %s", describe_proxy(proxy), exc)
        return None


async def measured_egress(proxy: Optional[str], *, session_name: str) -> Optional[str]:
    """:func:`measure_egress`, and a guarantee that it cannot cost a registration.

    Guarded here as well as inside :func:`measure_egress`, because the rule is
    that describing an exit is never the reason a login did not happen — and a
    rule that holds only inside one helper holds until somebody edits that
    helper.  By this point the address is already bound; this only reports it.
    """
    try:
        ip = await measure_egress(proxy)
    except Exception as exc:  # pragma: no cover - measure_egress swallows its own
        log.warning("egress check raised, continuing without it: %s", exc)
        ip = None
    log.info("phone_auth egress session=%s proxy=%s ip=%s", session_name[:16], describe_proxy(proxy), ip or "?")
    return ip


__all__ = [
    "PROXY_SCHEMES",
    "InvalidProxyUrl",
    "describe_proxy",
    "measure_egress",
    "measured_egress",
    "normalize_requested_proxy",
]
