"""Portable session strings.

Version 2 (``rbg2.`` prefix): CRC32 + zlib-compressed JSON, base64url without
padding.  The legacy format written by rubigram 0.1 (plain base64url JSON,
no prefix) is still accepted by :func:`load_session_string`.

The string contains the auth key and the login private key; treat it like a
password.
"""

from __future__ import annotations

import base64
import binascii
import json
import zlib
from typing import Any

from rubigram.errors import StorageError

PREFIX_V2 = "rbg2."


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
        raise StorageError("Session string is not valid base64url") from exc


def dump_session_string(data: dict[str, Any]) -> str:
    """Serialize a session dict into a v2 session string."""
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False, sort_keys=True).encode("utf-8")
    checksum = zlib.crc32(raw).to_bytes(4, "big")
    return PREFIX_V2 + _b64encode(checksum + zlib.compress(raw, 9))


def load_session_string(session_string: str) -> dict[str, Any]:
    """Parse a v2 or legacy session string into a dict.

    Raises :class:`~rubigram.errors.StorageError` when the string is corrupt.
    """
    value = (session_string or "").strip()
    if not value:
        raise StorageError("Session string is empty")
    if value.startswith(PREFIX_V2):
        payload = _b64decode(value[len(PREFIX_V2) :])
        if len(payload) < 5:
            raise StorageError("Session string is truncated")
        checksum, compressed = payload[:4], payload[4:]
        try:
            raw = zlib.decompress(compressed)
        except zlib.error as exc:
            raise StorageError("Session string is corrupt") from exc
        if zlib.crc32(raw).to_bytes(4, "big") != checksum:
            raise StorageError("Session string checksum mismatch")
    else:
        raw = _b64decode(value)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise StorageError("Session string does not contain valid JSON") from exc
    if not isinstance(data, dict):
        raise StorageError("Session string does not contain a session object")
    return data


def session_string_version(session_string: str) -> int:
    return 2 if (session_string or "").strip().startswith(PREFIX_V2) else 1


__all__ = ["PREFIX_V2", "dump_session_string", "load_session_string", "session_string_version"]
