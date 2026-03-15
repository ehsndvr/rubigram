from __future__ import annotations

import random
import secrets
import string
from datetime import datetime
from typing import Optional


def generate_tmp_session(length: int = 32, alphabet: str = string.ascii_lowercase) -> str:
    """Generate a random temporary session string."""
    return "".join(random.choice(alphabet) for _ in range(length))


def generate_device_hash(length: int = 26) -> str:
    """Generate a browser-like numeric device hash for registerDevice."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def timestamp_to_datetime(ts: Optional[int]) -> Optional[datetime]:
    """Convert Unix timestamp to datetime."""
    return datetime.fromtimestamp(ts) if ts is not None else None


def datetime_to_timestamp(dt: Optional[datetime]) -> Optional[int]:
    """Convert datetime to Unix timestamp."""
    return int(dt.timestamp()) if dt is not None else None


def safe_int(value: Optional[str], default: int = 0) -> int:
    """Safely convert a string to int, returning default on failure."""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


__all__ = [
    "generate_tmp_session",
    "generate_device_hash",
    "timestamp_to_datetime",
    "datetime_to_timestamp",
    "safe_int",
]
