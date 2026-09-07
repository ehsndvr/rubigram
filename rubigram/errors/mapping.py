"""Mapping of Rubika ``status`` / ``status_det`` pairs to exception classes.

The values below are the complete enums used by web.rubika.ir 4.4.34
(``Su`` for ``status`` and ``Cu`` for ``status_det`` in the bundle).
"""

from __future__ import annotations

from typing import Any, Optional

from .exceptions import (
    CodeIsExpired,
    CodeIsInvalid,
    CodeIsUsed,
    InvalidAuth,
    InvalidInput,
    InvalidMethod,
    NotRegistered,
    NotSupportedApiVersion,
    RpcError,
    ServerError,
    TooRequests,
    Undeliverable,
    UsernameExists,
    extract_show_message,
)

STATUS_OK = "OK"
STATUS_VALUES = (
    "OK",
    "ERROR_TRY_AGAIN",
    "ERROR_IGNORE",
    "ERROR_MESSAGE_TRY",
    "ERROR_MESSAGE_IGN",
    "ERROR_GENERIC",
    "ERROR_ACTION",
)
STATUS_DET_VALUES = (
    "OK",
    "INVALID_INPUT",
    "NOT_SUPPORTED_API_VERSION",
    "SERVER_ERROR",
    "INVALID_METHOD",
    "CODE_IS_USED",
    "CODE_IS_EXPIRED",
    "INVALID_AUTH",
    "NOT_REGISTERED",
    "TOO_REQUESTS",
    "USERNAME_EXIST",
    "UNDELIVERABLE",
)

STATUS_DET_MAP: dict[str, type[RpcError]] = {
    "INVALID_INPUT": InvalidInput,
    "NOT_SUPPORTED_API_VERSION": NotSupportedApiVersion,
    "SERVER_ERROR": ServerError,
    "INVALID_METHOD": InvalidMethod,
    "CODE_IS_USED": CodeIsUsed,
    "CODE_IS_EXPIRED": CodeIsExpired,
    "INVALID_AUTH": InvalidAuth,
    "NOT_REGISTERED": NotRegistered,
    "TOO_REQUESTS": TooRequests,
    "USERNAME_EXIST": UsernameExists,
    "UNDELIVERABLE": Undeliverable,
}

# Older Rubika builds sometimes put the detail into ``status`` itself.
_LEGACY_STATUS_HINTS = {
    "TOO_REQUESTS": TooRequests,
    "INVALID_AUTH": InvalidAuth,
    "NOT_REGISTERED": NotRegistered,
    "INVALID_INPUT": InvalidInput,
}

_LOGIN_METHODS = {"signIn", "signUp", "checkTwoStepPasscode", "loginDisableTwoStep"}


def is_ok(payload: Any) -> bool:
    """True when a server payload carries ``status == "OK"`` (or no status at all)."""
    if not isinstance(payload, dict):
        return True
    status = payload.get("status")
    return status is None or status == STATUS_OK


def map_rpc_error(
    status: str,
    status_det: Optional[str] = None,
    raw: Optional[dict[str, Any]] = None,
    *,
    method: Optional[str] = None,
) -> RpcError:
    """Build the most specific :class:`RpcError` for a status pair.

    ``raw`` should be the decrypted payload so that ``client_show_message`` is
    available on the exception.
    """
    detail = (status_det or "").strip().upper() or None
    outer = (status or "").strip().upper()
    show_message = extract_show_message(raw)

    error_cls = STATUS_DET_MAP.get(detail or "")
    if error_cls is None:
        error_cls = _LEGACY_STATUS_HINTS.get(outer, RpcError)

    if error_cls is InvalidInput and method in _LOGIN_METHODS:
        error_cls = CodeIsInvalid

    if error_cls is TooRequests:
        return TooRequests(outer or status, status_det, raw, method=method, client_show_message=show_message)
    return error_cls(outer or status, status_det, raw, method=method, client_show_message=show_message)


def raise_for_status(payload: Any, *, method: Optional[str] = None) -> None:
    """Raise the mapped :class:`RpcError` when ``payload`` is not ``OK``."""
    if is_ok(payload):
        return
    raise map_rpc_error(
        str(payload.get("status")),
        payload.get("status_det"),
        payload,
        method=method,
    )


__all__ = [
    "STATUS_OK",
    "STATUS_VALUES",
    "STATUS_DET_VALUES",
    "STATUS_DET_MAP",
    "is_ok",
    "map_rpc_error",
    "raise_for_status",
]
