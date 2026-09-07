"""SQLite file storage (``<workdir>/<name>.session``) with automatic migration.

The schema is derived from :data:`rubigram.storage.base.FIELDS`.  Files
written by any earlier rubigram version are upgraded in place: missing
columns are added, the single session row is guaranteed to exist and the
``meta.version`` is bumped.  Nothing is ever dropped.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional, Union

from rubigram.errors import StorageError

from .base import FIELDS, Field, Storage, decode_value, encode_value

SCHEMA_VERSION = 2

_SQL_TYPES = {"text": "TEXT", "int": "INTEGER", "bool": "INTEGER", "json": "TEXT"}


def _column_definitions() -> str:
    parts = ["id INTEGER PRIMARY KEY CHECK (id = 1)"]
    for field in FIELDS:
        if field.name == "api_version":
            parts.append("api_version TEXT NOT NULL")
        else:
            parts.append(f"{field.column} {_SQL_TYPES[field.kind]}")
    parts.append("created_at INTEGER NOT NULL")
    parts.append("updated_at INTEGER NOT NULL")
    return ",\n    ".join(parts)


def build_schema() -> str:
    return (
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);\n"
        f"CREATE TABLE IF NOT EXISTS session (\n    {_column_definitions()}\n);"
    )


class SqliteStorage(Storage):
    """Persistent storage in a single-row SQLite database."""

    FILE_EXTENSION = ".session"

    def __init__(self, name: str, workdir: Union[str, Path] = Path(".")):
        super().__init__(name)
        self.workdir = Path(workdir)
        self.database = self.workdir / f"{name}{self.FILE_EXTENSION}"
        self.conn: Optional[sqlite3.Connection] = None

    @property
    def is_open(self) -> bool:
        return self.conn is not None

    async def open(self) -> None:
        if self.conn is not None:
            return
        try:
            self.database.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.database), timeout=30, check_same_thread=False)
            self._migrate()
        except sqlite3.Error as exc:
            self.conn = None
            raise StorageError(f"Cannot open session file {self.database}: {exc}") from exc

    def _migrate(self) -> None:
        assert self.conn is not None
        now = int(time.time())
        with self.conn:
            self.conn.executescript(build_schema())
            columns = {row[1] for row in self.conn.execute("PRAGMA table_info(session)").fetchall()}
            for field in FIELDS:
                if field.column not in columns:
                    self.conn.execute(f"ALTER TABLE session ADD COLUMN {field.column} {_SQL_TYPES[field.kind]}")
            self.conn.execute(
                "INSERT OR IGNORE INTO session (id, api_version, created_at, updated_at) VALUES (1, ?, ?, ?)",
                (str(FIELDS[0].default), now, now),
            )
            self.conn.execute("UPDATE session SET registered_device = COALESCE(registered_device, 0) WHERE id = 1")
            self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('version', ?)", (str(SCHEMA_VERSION),))

    def _require_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            raise StorageError("Storage is not open; call open() first")
        return self.conn

    def _get(self, field: Field) -> Any:
        conn = self._require_conn()
        row = conn.execute(f"SELECT {field.column} FROM session WHERE id = 1").fetchone()
        return decode_value(field, row[0] if row else None)

    def _set(self, field: Field, value: Any) -> None:
        conn = self._require_conn()
        if field.name == "api_version" and value is None:
            value = field.default
        with conn:
            conn.execute(
                f"UPDATE session SET {field.column} = ?, updated_at = ? WHERE id = 1",
                (encode_value(field, value), int(time.time())),
            )

    async def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    async def delete(self) -> None:
        await self.close()
        try:
            os.remove(self.database)
        except FileNotFoundError:
            return

    def schema_version(self) -> int:
        conn = self._require_conn()
        row = conn.execute("SELECT value FROM meta WHERE key = 'version'").fetchone()
        return int(row[0]) if row and str(row[0]).isdigit() else 0


# Names used by rubigram 0.1.
FileStorage = SqliteStorage
SQLiteStorage = SqliteStorage

__all__ = ["SqliteStorage", "FileStorage", "SQLiteStorage", "SCHEMA_VERSION", "build_schema"]
