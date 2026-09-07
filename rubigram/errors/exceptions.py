"""Exception hierarchy of rubigram.

Every error raised by the library derives from :class:`RubigramError`
(``RubikaError`` is kept as an alias).  Server-side failures are
:class:`RpcError` instances carrying the raw ``status`` / ``status_det`` pair
returned by Rubika, the decrypted payload and, when the server attached one,
the human readable ``client_show_message``.
"""

from __future__ import annotations

import re
from typing import Any, Optional


class RubigramError(Exception):
    """Base class for every error raised by rubigram."""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


RubikaError = RubigramError


# ---------------------------------------------------------------------------
# Transport / local errors
# ---------------------------------------------------------------------------


class TransportError(RubigramError):
    """A transport-level problem (bad HTTP status, malformed body, closed socket)."""


class NetworkError(TransportError):
    """The request never produced a usable response (connection or timeout)."""

    def __init__(self, message: str = "", original_error: Optional[BaseException] = None):
        super().__init__(message)
        self.original_error = original_error


class RequestTimeout(NetworkError):
    """The request exceeded its timeout on every retry."""


class DecodeError(RubigramError):
    """Decryption or JSON parsing of a server payload failed."""


class StorageError(RubigramError):
    """Session storage could not be read or written."""


class AuthError(RubigramError):
    """Authentication state is missing or unusable."""


class LoginRequired(AuthError):
    """The method needs an authenticated session and none is stored."""


class TmpSessionRequired(AuthError):
    """A login method needs a temporary session and none is available."""


class SessionExpired(AuthError):
    """The server declared the stored session dead (``INVALID_AUTH`` with ``ERROR_ACTION``)."""


class BotApiError(RubigramError):
    """The Bot API answered ``ok: false``."""

    def __init__(self, message: str = "", *, error_code: Optional[int] = None, raw: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.raw = raw


# ---------------------------------------------------------------------------
# RPC errors
# ---------------------------------------------------------------------------


_DURATION_PATTERNS = (
    (re.compile(r"(\d+)\s*(?:second|seconds|ثانیه)"), 1),
    (re.compile(r"(\d+)\s*(?:minute|minutes|دقیقه)"), 60),
    (re.compile(r"(\d+)\s*(?:hour|hours|ساعت)"), 3600),
    (re.compile(r"(\d+)\s*(?:day|days|روز)"), 86400),
)


def extract_show_message(raw: Optional[dict[str, Any]]) -> Optional[str]:
    """Return the human readable text of a ``client_show_message`` block, if any.

    Rubika nests the text differently per message kind
    (``link.alert_data.message``, ``text``, ``title`` …); the first string found
    under one of those keys wins.
    """
    if not isinstance(raw, dict):
        return None
    block = raw.get("client_show_message")
    if not isinstance(block, dict):
        return None

    def walk(node: Any) -> Optional[str]:
        if isinstance(node, dict):
            for key in ("message", "text", "title", "description"):
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            for value in node.values():
                found = walk(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return None

    return walk(block)


def parse_retry_after(text: Optional[str]) -> Optional[float]:
    """Best-effort extraction of a wait duration (seconds) from a server message."""
    if not text:
        return None
    normalized = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    for pattern, factor in _DURATION_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return float(match.group(1)) * factor
    return None


class RpcError(RubigramError):
    """The server answered with a non-``OK`` status.

    Attributes:
        status: outer status (``ERROR_GENERIC``, ``ERROR_ACTION`` …).
        status_det: detailed status (``INVALID_INPUT``, ``INVALID_AUTH`` …).
        raw: the decrypted response payload (or the plain response for
            unencrypted calls); ``None`` when unavailable.
        method: the RPC method name that failed, when known.
        client_show_message: the server's human readable message, if any.
    """

    status_det_name: Optional[str] = None

    def __init__(
        self,
        status: str,
        status_det: Optional[str] = None,
        raw: Optional[dict[str, Any]] = None,
        *,
        method: Optional[str] = None,
        client_show_message: Optional[str] = None,
    ):
        self.status = status
        self.status_det = status_det
        self.raw = raw
        self.method = method
        self.client_show_message = client_show_message or extract_show_message(raw)
        # Kept for code that read ``error.MESSAGE`` on the old classes.
        self.MESSAGE = status_det or status
        parts = [status]
        if status_det:
            parts.append(status_det)
        text = ": ".join(parts)
        if method:
            text = f"{method} -> {text}"
        if self.client_show_message:
            text = f"{text} ({self.client_show_message})"
        super().__init__(text)

    @property
    def is_session_dead(self) -> bool:
        """True when the server wants the client to log out (``ERROR_ACTION``)."""
        return self.status == "ERROR_ACTION"


class InvalidInput(RpcError):
    """``INVALID_INPUT``: the server rejected the request fields."""

    status_det_name = "INVALID_INPUT"


class CodeIsInvalid(InvalidInput):
    """``INVALID_INPUT`` returned by ``signIn``: the verification code is wrong."""


PhoneCodeInvalid = CodeIsInvalid


class PhoneHashInvalid(InvalidInput):
    """``INVALID_INPUT`` for a stale ``phone_code_hash`` (request a new code)."""


class NotSupportedApiVersion(RpcError):
    status_det_name = "NOT_SUPPORTED_API_VERSION"


class ServerError(RpcError):
    status_det_name = "SERVER_ERROR"


class InvalidMethod(RpcError):
    status_det_name = "INVALID_METHOD"


class CodeIsUsed(RpcError):
    status_det_name = "CODE_IS_USED"


class CodeIsExpired(RpcError):
    status_det_name = "CODE_IS_EXPIRED"


class InvalidAuth(RpcError):
    """``INVALID_AUTH``: the auth key is unknown to the server.

    With ``status == "ERROR_ACTION"`` the session is dead and must be
    recreated; with ``ERROR_GENERIC`` the server only denied this action.
    """

    status_det_name = "INVALID_AUTH"


AuthKeyInvalid = InvalidAuth


class NotRegistered(RpcError):
    """``NOT_REGISTERED``: ``registerDevice`` must be called before retrying."""

    status_det_name = "NOT_REGISTERED"


RegisterDeviceRequired = NotRegistered


class TooRequests(RpcError):
    """``TOO_REQUESTS``: rate limited.  ``retry_after`` is in seconds when known."""

    status_det_name = "TOO_REQUESTS"

    def __init__(
        self,
        status: str,
        status_det: Optional[str] = None,
        raw: Optional[dict[str, Any]] = None,
        *,
        method: Optional[str] = None,
        client_show_message: Optional[str] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(status, status_det, raw, method=method, client_show_message=client_show_message)
        self.retry_after = retry_after if retry_after is not None else parse_retry_after(self.client_show_message)

    @property
    def wait_time(self) -> Optional[float]:
        """Alias kept for the old ``FloodWaitError.wait_time``."""
        return self.retry_after


FloodWaitError = TooRequests


class UsernameExists(RpcError):
    status_det_name = "USERNAME_EXIST"


class Undeliverable(RpcError):
    status_det_name = "UNDELIVERABLE"


__all__ = [
    "AuthError",
    "AuthKeyInvalid",
    "BotApiError",
    "CodeIsExpired",
    "CodeIsInvalid",
    "CodeIsUsed",
    "DecodeError",
    "FloodWaitError",
    "InvalidAuth",
    "InvalidInput",
    "InvalidMethod",
    "LoginRequired",
    "NetworkError",
    "NotRegistered",
    "NotSupportedApiVersion",
    "PhoneCodeInvalid",
    "PhoneHashInvalid",
    "RegisterDeviceRequired",
    "RequestTimeout",
    "RpcError",
    "RubigramError",
    "RubikaError",
    "ServerError",
    "SessionExpired",
    "StorageError",
    "TmpSessionRequired",
    "TooRequests",
    "TransportError",
    "Undeliverable",
    "UsernameExists",
    "extract_show_message",
    "parse_retry_after",
]
