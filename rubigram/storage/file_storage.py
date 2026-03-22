"""File-based SQLite session storage."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .sqlite_storage import SQLiteStorage


class FileStorage(SQLiteStorage):
    """Store the session as a .session SQLite file."""

    FILE_EXTENSION = ".session"

    def __init__(self, name: str, workdir: Path):
        super().__init__(name)
        self.database = workdir / (self.name + self.FILE_EXTENSION)

    async def open(self) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)

        file_exists = self.database.is_file()
        self.conn = sqlite3.connect(str(self.database), timeout=30, check_same_thread=False)

        if not file_exists:
            self._create_new_db()
        else:
            # Ensure tables exist even if the file was created by an older version.
            with self.conn:
                self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS session (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    api_version TEXT NOT NULL,
                    api_url TEXT,
                    api_urls_json TEXT,
                    storages_json TEXT,
                    cdn_urls_json TEXT,
                    sockets_json TEXT,
                    auth TEXT,
                    tmp_session TEXT,
                    public_key TEXT,
                    private_key_pem TEXT,
                    user_guid TEXT,
                    updates_state INTEGER,
                    device_hash TEXT,
                    registered_device INTEGER,
                    registered_device_version TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                """)
                columns = {row[1] for row in self.conn.execute("PRAGMA table_info(session)").fetchall()}
                if "public_key" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN public_key TEXT")
                if "private_key_pem" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN private_key_pem TEXT")
                if "updates_state" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN updates_state INTEGER")
                if "device_hash" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN device_hash TEXT")
                if "registered_device" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN registered_device INTEGER")
                if "registered_device_version" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN registered_device_version TEXT")
                if "bot_token" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN bot_token TEXT")
                if "bot_offset_id" not in columns:
                    self.conn.execute("ALTER TABLE session ADD COLUMN bot_offset_id TEXT")
                # Make sure the session row exists.
                now = int(__import__("time").time())
                self.conn.execute(
                    "INSERT OR IGNORE INTO session (id, api_version, created_at, updated_at) VALUES (1, ?, ?, ?)",
                    ("6", now, now),
                )
                self.conn.execute(
                    "UPDATE session SET registered_device = COALESCE(registered_device, 0) WHERE id = 1"
                )

    async def delete(self) -> None:
        try:
            os.remove(self.database)
        except FileNotFoundError:
            return
