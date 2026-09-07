"""In-memory storage: nothing touches the disk; state survives close/open."""

from __future__ import annotations

from typing import Any, Optional

from rubigram.errors import StorageError

from .base import FIELDS, Field, Storage, decode_value, encode_value
from .session_codec import load_session_string


class MemoryStorage(Storage):
    """Dict-backed storage, optionally seeded from a session string."""

    def __init__(self, name: str, session_string: Optional[str] = None):
        super().__init__(name)
        self._session_string = session_string
        self._values: dict[str, Any] = {field.name: encode_value(field, field.default) for field in FIELDS}
        self._open = False
        self._seeded = False

    @property
    def is_open(self) -> bool:
        return self._open

    async def open(self) -> None:
        self._open = True
        if self._session_string and not self._seeded:
            self._seeded = True
            await self.import_session_dict(load_session_string(self._session_string))

    def _get(self, field: Field) -> Any:
        if not self._open:
            raise StorageError("Storage is not open; call open() first")
        return decode_value(field, self._values.get(field.name))

    def _set(self, field: Field, value: Any) -> None:
        if not self._open:
            raise StorageError("Storage is not open; call open() first")
        if field.name == "api_version" and value is None:
            value = field.default
        self._values[field.name] = encode_value(field, value)

    async def close(self) -> None:
        self._open = False

    async def delete(self) -> None:
        self._values = {field.name: encode_value(field, field.default) for field in FIELDS}


__all__ = ["MemoryStorage"]
