"""rubigram: an async Python client for Rubika (phone-number sessions and bots)."""

from . import crypto, enums, errors, filters, handlers, raw, storage, types
from .client import Client, CodeCallback
from .errors import (
    AuthError,
    BotApiError,
    DecodeError,
    InvalidAuth,
    InvalidInput,
    LoginRequired,
    NetworkError,
    NotRegistered,
    RpcError,
    RubigramError,
    RubikaError,
    TooRequests,
    TransportError,
)
from .handlers import ContinuePropagation, Handler, MessageHandler, StopPropagation
from .network import RetryPolicy, Transport
from .peer import Peer
from .version import __version__

__all__ = [
    "Client",
    "CodeCallback",
    "Transport",
    "RetryPolicy",
    "Peer",
    "__version__",
    # namespaces
    "crypto",
    "enums",
    "errors",
    "filters",
    "handlers",
    "raw",
    "storage",
    "types",
    # errors
    "RubigramError",
    "RubikaError",
    "TransportError",
    "NetworkError",
    "DecodeError",
    "AuthError",
    "LoginRequired",
    "RpcError",
    "InvalidInput",
    "InvalidAuth",
    "NotRegistered",
    "TooRequests",
    "BotApiError",
    # handlers
    "Handler",
    "MessageHandler",
    "StopPropagation",
    "ContinuePropagation",
]
