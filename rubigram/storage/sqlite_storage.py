"""Deprecated module name; use :mod:`rubigram.storage.sqlite` / :mod:`rubigram.storage.base`."""

from rubigram.storage.base import Storage
from rubigram.storage.sqlite import SqliteStorage, SQLiteStorage

__all__ = ["Storage", "SqliteStorage", "SQLiteStorage"]
