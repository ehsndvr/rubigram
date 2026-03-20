from __future__ import annotations

from enum import Enum


class ParseMode(str, Enum):
    DEFAULT = "default"
    MARKDOWN = "markdown"
    HTML = "html"
