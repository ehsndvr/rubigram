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
    "AuthError",
    "BotApiError",
    "Client",
    "CodeCallback",
    "ContinuePropagation",
    "DecodeError",
    # handlers
    "Handler",
    "InvalidAuth",
    "InvalidInput",
    "LoginRequired",
    "MessageHandler",
    "NetworkError",
    "NotRegistered",
    "Peer",
    "RetryPolicy",
    "RpcError",
    # errors
    "RubigramError",
    "RubikaError",
    "StopPropagation",
    "TooRequests",
    "Transport",
    "TransportError",
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
]
