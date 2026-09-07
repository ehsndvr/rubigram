"""Deprecated package: the Bot API is part of :class:`rubigram.Client` (``token=...``).

``rubigram.bot.types`` and ``rubigram.bot.enums`` re-export
:mod:`rubigram.types.bot` and :mod:`rubigram.enums.bot`.
"""

from rubigram.enums import bot as enums
from rubigram.types import bot as types

__all__ = ["enums", "types"]
