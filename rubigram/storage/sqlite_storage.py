"""Deprecated module name; use :mod:`rubigram.storage.sqlite` / :mod:`rubigram.storage.base`."""

from rubigram.storage.base import Storage
from rubigram.storage.sqlite import SQLiteStorage, SqliteStorage

__all__ = ["SQLiteStorage", "SqliteStorage", "Storage"]
