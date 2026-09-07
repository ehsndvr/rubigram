"""Transport selection.

Rubika's web protocol carries every RPC over HTTPS; the WebSocket only
delivers server pushes.  The :class:`Transport` mode therefore selects how a
client stays connected and receives updates:

- ``Transport.WS`` (default): a socket is opened after login and pushed
  updates are dispatched to handlers.
- ``Transport.HTTP``: no socket is ever opened; updates are fetched by
  polling (``get_updates``) when the application asks for them.
"""

from __future__ import annotations

from enum import Enum


class Transport(str, Enum):
    """Update delivery mode of a :class:`~rubigram.Client`."""

    WS = "ws"
    HTTP = "http"

    @property
    def is_http(self) -> bool:
        return self is Transport.HTTP

    @property
    def is_ws(self) -> bool:
        return self is Transport.WS

    @classmethod
    def coerce(cls, value: str | Transport) -> Transport:
        """Normalize ``value`` (``"ws"``/``"http"`` or a member) to a member.

        Raises ``ValueError`` for anything else so a typo fails at the call site.
        """
        if isinstance(value, Transport):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            aliases = {"websocket": "ws", "socket": "ws", "https": "http", "web": "ws"}
            normalized = aliases.get(normalized, normalized)
            for member in cls:
                if member.value == normalized:
                    return member
        raise ValueError(f"unknown transport mode: {value!r} (expected 'ws' or 'http')")


__all__ = ["Transport"]
