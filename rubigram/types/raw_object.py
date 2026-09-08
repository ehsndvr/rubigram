"""Untyped result objects."""

from __future__ import annotations

from typing import Any

from .object import Object, _parse_dynamic


class RawObject(Object):
    """A server object exposed as attributes without a declared schema.

    Every key of the payload becomes an attribute; nested dicts become
    :class:`RawObject` instances and lists are converted element-wise.
    ``raw_object.to_dict()`` returns the original data.
    """

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client=client)
        for key, value in kwargs.items():
            self.extra[key] = value
            if key.isidentifier() and not key.startswith("_"):
                setattr(self, key, value)

    @classmethod
    def _parse(cls, client: Any, data: Any) -> Any:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        if isinstance(data, list):
            return [_parse_dynamic(client, item) for item in data]
        if not isinstance(data, dict):
            return data
        return cls(client=client, **{key: _parse_dynamic(client, value) for key, value in data.items()})

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style access for keys that are not valid identifiers."""
        return self.extra.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self.extra

    def __bool__(self) -> bool:
        return True


class Empty(RawObject):
    """Result of methods whose response carries no data."""


__all__ = ["Empty", "RawObject"]
