from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rubigram.enums import MessageEntityType


@dataclass(frozen=True)
class MessageEntity:
    type: MessageEntityType | str
    offset: int
    length: int

    def to_metadata_part(self) -> dict[str, Any]:
        entity_type = self.type.value if hasattr(self.type, "value") else str(self.type)
        return {
            "type": entity_type,
            "from_index": self.offset,
            "length": self.length,
        }

    @classmethod
    def bold(cls, offset: int, length: int) -> "MessageEntity":
        return cls(MessageEntityType.BOLD, offset, length)

    @classmethod
    def italic(cls, offset: int, length: int) -> "MessageEntity":
        return cls(MessageEntityType.ITALIC, offset, length)

    @classmethod
    def mono(cls, offset: int, length: int) -> "MessageEntity":
        return cls(MessageEntityType.MONO, offset, length)

    @classmethod
    def mention(cls, offset: int, length: int) -> "MessageEntity":
        return cls(MessageEntityType.MENTION, offset, length)
