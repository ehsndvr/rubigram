from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Peer:
    id: str
    type: str | None = None

    @property
    def object_guid(self) -> str:
        return self.id

    @property
    def user_guid(self) -> str:
        return self.id

    @classmethod
    def from_value(cls, value: Any) -> Peer:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(id=value)

        for attr in ("object_guid", "user_guid", "chat_id", "guid", "id"):
            candidate = getattr(value, attr, None)
            if candidate is not None:
                return cls(id=str(candidate), type=getattr(value, "type", None))

        raise TypeError(f"Unsupported peer value: {type(value)!r}")
