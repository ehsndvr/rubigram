"""Deprecated: import from :mod:`rubigram.errors` instead.

This module re-exports the whole error hierarchy so that
``from rubigram.exceptions import InvalidInput`` keeps working; it will be
removed in a future major version.
"""

from __future__ import annotations

import warnings

from rubigram.errors import *  # noqa: F401,F403
from rubigram.errors import __all__ as _all

warnings.warn(
    "rubigram.exceptions is deprecated; import from rubigram.errors instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = list(_all)
