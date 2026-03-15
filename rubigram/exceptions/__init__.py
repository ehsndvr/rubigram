from __future__ import annotations

from typing import Any, Optional


class RubikaError(Exception):
    """Base exception for all Rubika library errors."""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class AuthError(RubikaError):
    """Raised when authentication fails or is required."""


class LoginRequired(RubikaError):
    """Raised when a method requires authentication but none is available."""


class TmpSessionRequired(RubikaError):
    """Raised when a login method requires a temporary session."""


class RpcError(RubikaError):
    """Raised when the server returns a non-OK status in the response."""

    def __init__(
        self,
        status: str,
        status_det: Optional[str] = None,
        raw: Optional[dict[str, Any]] = None,
    ):
        self.status = status
        self.status_det = status_det
        self.raw = raw
        self.MESSAGE = status_det or status
        message = f"{status}: {status_det or ''}" if status_det else status
        super().__init__(message)


class CodeIsInvalid(RpcError):
    """Raised when the verification code is invalid."""


class PhoneCodeInvalid(RpcError):
    """Raised when the phone code is invalid."""


class PhoneHashInvalid(RpcError):
    """Raised when the phone code hash is invalid."""


class AuthKeyInvalid(RpcError):
    """Raised when the auth key is invalid or expired."""


class InvalidInput(RpcError):
    """Raised when the server rejects malformed input."""


class NotSupportedApiVersion(RpcError):
    """Raised when the server rejects the API version."""


class ServerError(RpcError):
    """Raised when the server reports an internal error."""


class InvalidMethod(RpcError):
    """Raised when the server does not recognize the requested method."""


class CodeIsUsed(RpcError):
    """Raised when the verification code has already been used."""


class CodeIsExpired(RpcError):
    """Raised when the verification code has expired."""


class TooRequests(RpcError):
    """Raised when the server rate-limits the request."""


class UsernameExists(RpcError):
    """Raised when attempting to use an already-taken username."""


class Undeliverable(RpcError):
    """Raised when the server cannot deliver the requested action."""


class NetworkError(RubikaError):
    """Raised when a network error occurs."""

    def __init__(self, message: str = "", original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class TransportError(RubikaError):
    """Raised when transport layer errors occur."""


class DecodeError(RubikaError):
    """Raised when decryption or parsing fails."""


class StorageError(RubikaError):
    """Raised when storage operations fail."""


class SessionExpired(RubikaError):
    """Raised when the session has expired."""


class RegisterDeviceRequired(RpcError):
    """Raised when the server requires a registerDevice call before continuing."""


class FloodWaitError(RubikaError):
    """Raised when the user is rate-limited by the server."""

    def __init__(self, message: str = "", wait_time: Optional[int] = None):
        super().__init__(message)
        self.wait_time = wait_time


def map_rpc_error(
    status: str,
    status_det: Optional[str] = None,
    raw: Optional[dict[str, Any]] = None,
) -> RubikaError:
    """Map a Rubika status/status_det pair to the best known RPC error."""
    message = " ".join(part for part in [status, status_det] if part).lower()

    if "code" in message and "invalid" in message:
        return CodeIsInvalid(status, status_det, raw)
    if "phone_code" in message and "invalid" in message:
        return PhoneCodeInvalid(status, status_det, raw)
    if "phone_hash" in message and "invalid" in message:
        return PhoneHashInvalid(status, status_det, raw)
    if "invalid_input" in message or ("input" in message and "invalid" in message):
        return InvalidInput(status, status_det, raw)
    if "not_supported_api_version" in message:
        return NotSupportedApiVersion(status, status_det, raw)
    if "server_error" in message:
        return ServerError(status, status_det, raw)
    if "invalid_method" in message:
        return InvalidMethod(status, status_det, raw)
    if "code_is_used" in message:
        return CodeIsUsed(status, status_det, raw)
    if "code_is_expired" in message:
        return CodeIsExpired(status, status_det, raw)
    if "too_requests" in message:
        return TooRequests(status, status_det, raw)
    if "username_exist" in message:
        return UsernameExists(status, status_det, raw)
    if "undeliverable" in message:
        return Undeliverable(status, status_det, raw)
    if "auth" in message and ("invalid" in message or "expired" in message):
        return AuthKeyInvalid(status, status_det, raw)
    if "login" in message and "required" in message:
        return LoginRequired(f"{status}: {status_det or ''}".strip())
    if "not_registered" in message or ("not" in message and "registered" in message):
        return RegisterDeviceRequired(status, status_det, raw)
    if "tmp" in message and "session" in message:
        return TmpSessionRequired(f"{status}: {status_det or ''}".strip())
    if "session" in message and "expired" in message:
        return SessionExpired(f"{status}: {status_det or ''}".strip())

    return RpcError(status, status_det, raw)


__all__ = [
    "RubikaError",
    "AuthError",
    "LoginRequired",
    "TmpSessionRequired",
    "RpcError",
    "CodeIsInvalid",
    "PhoneCodeInvalid",
    "PhoneHashInvalid",
    "AuthKeyInvalid",
    "InvalidInput",
    "NotSupportedApiVersion",
    "ServerError",
    "InvalidMethod",
    "CodeIsUsed",
    "CodeIsExpired",
    "TooRequests",
    "UsernameExists",
    "Undeliverable",
    "NetworkError",
    "TransportError",
    "DecodeError",
    "StorageError",
    "SessionExpired",
    "RegisterDeviceRequired",
    "FloodWaitError",
    "map_rpc_error",
]
