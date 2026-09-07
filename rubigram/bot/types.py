"""Deprecated module name; import from :mod:`rubigram.types.bot`."""

from __future__ import annotations

import warnings

from rubigram.types.bot import *  # noqa: F403
from rubigram.types.bot import __all__ as _all

warnings.warn("rubigram.bot.types is deprecated; use rubigram.types.bot", DeprecationWarning, stacklevel=2)

__all__ = list(_all)  # pyright: ignore[reportUnsupportedDunderAll]
