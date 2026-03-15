"""Session string utilities.

Session strings are used to serialize a session into a short, portable form.
The format is JSON (UTF-8) encoded with base64url, without padding.

This keeps the format:
- human-debuggable (after base64 decode)
- forward-compatible (unknown keys can be ignored)
"""

from __future__ import annotations

import base64
import json
from typing import Any


def dump_session_string(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def load_session_string(session_string: str) -> dict[str, Any]:
    padded = session_string + "=" * (-len(session_string) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    return json.loads(raw.decode("utf-8"))
