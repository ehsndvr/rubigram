"""Deprecated module name; import from :mod:`rubigram.enums.bot`."""

from __future__ import annotations

import warnings

from rubigram.enums.bot import *  # noqa: F403
from rubigram.enums.bot import __all__ as _all

warnings.warn("rubigram.bot.enums is deprecated; use rubigram.enums.bot", DeprecationWarning, stacklevel=2)

__all__ = list(_all)  # pyright: ignore[reportUnsupportedDunderAll]
