"""Deprecated module name: every model now lives in a domain module of :mod:`rubigram.types`."""

from __future__ import annotations

import warnings

import rubigram.types as _types

warnings.warn(
    "rubigram.types.results is deprecated; import from rubigram.types instead",
    DeprecationWarning,
    stacklevel=2,
)

globals().update({name: getattr(_types, name) for name in _types.__all__})
__all__ = list(_types.__all__)  # pyright: ignore[reportUnsupportedDunderAll]
