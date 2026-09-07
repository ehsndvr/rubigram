"""Small helpers shared by the client and the mixins."""

from __future__ import annotations

import re
import secrets
import string
import time
from datetime import datetime
from typing import Optional

from .media import parse_ogg_opus_duration_ms
from .phone import looks_like_bot_token, looks_like_phone_number, normalize_phone_number


def generate_tmp_session(length: int = 32, alphabet: str = string.ascii_lowercase) -> str:
    """Random temporary session key used by the login flow (32 lowercase letters)."""
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_device_hash(length: int = 26) -> str:
    """Random numeric device hash for ``registerDevice``."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def device_hash_from_user_agent(user_agent: str, mime_types_count: int = 2) -> str:
    """The web client's ``getBrowserId``: mime type count followed by every digit of the user agent."""
    digits = re.sub(r"\D+", "", user_agent)
    return f"{mime_types_count}{digits}"


def new_rnd() -> str:
    """Unique ``rnd`` value for ``sendMessage``-style calls."""
    return str(time.time_ns())


def timestamp_to_datetime(ts: Optional[int]) -> Optional[datetime]:
    return datetime.fromtimestamp(ts) if ts is not None else None


def datetime_to_timestamp(dt: Optional[datetime]) -> Optional[int]:
    return int(dt.timestamp()) if dt is not None else None


def safe_int(value: Optional[str], default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


__all__ = [
    "generate_tmp_session",
    "generate_device_hash",
    "device_hash_from_user_agent",
    "new_rnd",
    "timestamp_to_datetime",
    "datetime_to_timestamp",
    "safe_int",
    "normalize_phone_number",
    "looks_like_phone_number",
    "looks_like_bot_token",
    "parse_ogg_opus_duration_ms",
]
