"""Deprecated module name; use :mod:`rubigram.network.http` and :mod:`rubigram.network.pool`."""

from rubigram.network.http import HttpTransport, JsonTransport, RpcTransport
from rubigram.network.pool import ApiUrlPool, UrlPool

__all__ = ["ApiUrlPool", "HttpTransport", "JsonTransport", "RpcTransport", "UrlPool"]
