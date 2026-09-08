"""HMAC request signing between the membership worker and the panel.

Every internal request carries three headers: a signature, a timestamp and a
nonce.  The signature is ``sha256=`` + HMAC-SHA256 over
``"<timestamp>.<nonce>." + body`` with the shared secret.  The receiver
rejects signatures older than ``max_age_seconds`` and stores nonces to refuse
replays.

The scheme (and the default ``X-Balegram-*`` header names) is wire-compatible
with the balegram panel, so a panel that already drives a Bale worker can drive
a rubigram worker without changes.  ``X-Rubigram-*`` headers are accepted too.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

DEFAULT_HEADER_PREFIX = "X-Balegram"
ACCEPTED_HEADER_PREFIXES = ("X-Balegram", "X-Rubigram")

SIGNATURE_HEADER = f"{DEFAULT_HEADER_PREFIX}-Signature"
TIMESTAMP_HEADER = f"{DEFAULT_HEADER_PREFIX}-Timestamp"
NONCE_HEADER = f"{DEFAULT_HEADER_PREFIX}-Nonce"


class SignatureError(ValueError):
    """Raised when an internal request signature is missing, expired or wrong."""


@dataclass(frozen=True)
class VerifiedSignature:
    timestamp: int
    nonce: str


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    """The byte form that is signed: compact JSON with sorted keys, UTF-8."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _message(timestamp: str, nonce: str, body: bytes) -> bytes:
    return f"{timestamp}.{nonce}.".encode("ascii") + body


def _digest(secret: str, timestamp: str, nonce: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), _message(timestamp, nonce, body), hashlib.sha256).hexdigest()


def sign_body(
    body: bytes,
    *,
    secret: str,
    timestamp: int | None = None,
    nonce: str | None = None,
    header_prefix: str = DEFAULT_HEADER_PREFIX,
) -> dict[str, str]:
    """Headers that authenticate ``body``."""
    if not secret:
        raise SignatureError("internal shared secret is not configured")
    issued_at = str(timestamp if timestamp is not None else int(time.time()))
    request_nonce = nonce or secrets.token_urlsafe(18)
    return {
        f"{header_prefix}-Signature": f"sha256={_digest(secret, issued_at, request_nonce, body)}",
        f"{header_prefix}-Timestamp": issued_at,
        f"{header_prefix}-Nonce": request_nonce,
    }


def sign_json(payload: Mapping[str, Any], *, secret: str, header_prefix: str = DEFAULT_HEADER_PREFIX) -> tuple[bytes, dict[str, str]]:
    """Canonical body plus signature and content-type headers."""
    body = canonical_json(payload)
    headers = sign_body(body, secret=secret, header_prefix=header_prefix)
    headers["Content-Type"] = "application/json"
    return body, headers


def _header(headers: Mapping[str, str], suffix: str) -> str | None:
    for prefix in ACCEPTED_HEADER_PREFIXES:
        name = f"{prefix}-{suffix}"
        value = headers.get(name) or headers.get(name.lower())
        if value:
            return value
    return None


def verify_body(body: bytes, *, headers: Mapping[str, str], secret: str, max_age_seconds: int = 300) -> VerifiedSignature:
    """Check the signature headers of an incoming request; raises :class:`SignatureError`."""
    if not secret:
        raise SignatureError("internal shared secret is not configured")
    signature = _header(headers, "Signature")
    timestamp = _header(headers, "Timestamp")
    nonce = _header(headers, "Nonce")
    if not signature or not timestamp or not nonce:
        raise SignatureError("missing internal signature headers")
    if not signature.startswith("sha256="):
        raise SignatureError("unsupported signature format")
    try:
        issued_at = int(timestamp)
    except ValueError as exc:
        raise SignatureError("invalid signature timestamp") from exc
    if abs(int(time.time()) - issued_at) > max_age_seconds:
        raise SignatureError("expired internal signature")
    expected = f"sha256={_digest(secret, str(issued_at), nonce, body)}"
    if not hmac.compare_digest(signature, expected):
        raise SignatureError("invalid internal signature")
    return VerifiedSignature(timestamp=issued_at, nonce=nonce)


__all__ = [
    "ACCEPTED_HEADER_PREFIXES",
    "DEFAULT_HEADER_PREFIX",
    "NONCE_HEADER",
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "SignatureError",
    "VerifiedSignature",
    "canonical_json",
    "sign_body",
    "sign_json",
    "verify_body",
]
