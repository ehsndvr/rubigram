from __future__ import annotations

from enum import Enum


class MessageEntityType(str, Enum):
    BOLD = "Bold"
    ITALIC = "Italic"
    MONO = "Mono"
    MENTION = "Mention"
