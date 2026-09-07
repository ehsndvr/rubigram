"""Deprecated module name; use :mod:`rubigram.storage.sqlite`."""

from rubigram.storage.sqlite import FileStorage, SqliteStorage

__all__ = ["FileStorage", "SqliteStorage"]
