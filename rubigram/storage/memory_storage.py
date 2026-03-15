"""In-memory SQLite session storage.

This behaves similarly to Pyrogram's in-memory sessions:
- When created with a session_string, it will load its content.
- It can export itself back to a session_string.

Note: Because this is in-memory, data is lost when the process exits.
"""

from __future__ import annotations

import sqlite3

from .sqlite_storage import SQLiteStorage


class MemoryStorage(SQLiteStorage):
    def __init__(self, name: str, session_string: str | None = None):
        super().__init__(name)
        self._session_string = session_string

    async def open(self) -> None:
        self.conn = sqlite3.connect(":memory:", timeout=30, check_same_thread=False)
        self._create_new_db()

        if self._session_string:
            await self.import_session_string(self._session_string)

    async def delete(self) -> None:
        # No-op for memory storage.
        return
