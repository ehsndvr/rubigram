"""SQLite-based session storage for Rubigram sessions."""

from __future__ import annotations

import json
import sqlite3
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from .session_string import dump_session_string, load_session_string

# language=SQLite
SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS session (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    api_version   TEXT NOT NULL,
    api_url       TEXT,
    api_urls_json TEXT,
    storages_json TEXT,
    cdn_urls_json TEXT,
    sockets_json  TEXT,
    auth          TEXT,
    tmp_session   TEXT,
    public_key    TEXT,
    private_key_pem TEXT,
    user_guid     TEXT,
    updates_state INTEGER,
    device_hash   TEXT,
    registered_device INTEGER,
    registered_device_version TEXT,
    bot_token     TEXT,
    bot_offset_id TEXT,
    created_at    INTEGER NOT NULL,
    updated_at    INTEGER NOT NULL
);
"""


class SQLiteStorage(ABC):
    """Common SQLite logic shared by file and memory storage."""

    VERSION = 1

    def __init__(self, name: str):
        self.name = name
        self.conn: Optional[sqlite3.Connection] = None

    @abstractmethod
    async def open(self) -> None:
        """Open the underlying database connection."""

    @abstractmethod
    async def delete(self) -> None:
        """Delete the underlying storage, if applicable."""

    def _create_new_db(self) -> None:
        assert self.conn is not None

        with self.conn:
            self.conn.executescript(SCHEMA_V1)
            self.conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("version", str(self.VERSION)),
            )

            now = int(time.time())
            self.conn.execute(
                """
                INSERT OR IGNORE INTO session (
                    id, api_version, api_url, api_urls_json, storages_json, cdn_urls_json,
                    sockets_json, auth, tmp_session, public_key, private_key_pem, user_guid,
                    updates_state, device_hash, registered_device, registered_device_version, bot_token, bot_offset_id, created_at, updated_at
                ) VALUES (
                    1, ?, NULL, NULL, NULL, NULL,
                    NULL, NULL, NULL, NULL, NULL, NULL,
                    NULL,
                    NULL, 0, NULL, NULL, NULL, ?, ?
                )
                """,
                ("6", now, now),
            )

    def _touch(self) -> None:
        assert self.conn is not None
        with self.conn:
            self.conn.execute(
                "UPDATE session SET updated_at = ? WHERE id = 1",
                (int(time.time()),),
            )

    def _get_field(self, field: str) -> Any:
        assert self.conn is not None
        row = self.conn.execute(f"SELECT {field} FROM session WHERE id = 1").fetchone()
        return row[0] if row else None

    def _set_field(self, field: str, value: Any) -> None:
        assert self.conn is not None
        with self.conn:
            self.conn.execute(f"UPDATE session SET {field} = ? WHERE id = 1", (value,))
        self._touch()

    async def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    async def api_version(self) -> str:
        return str(self._get_field("api_version") or "6")

    async def set_api_version(self, value: str) -> None:
        self._set_field("api_version", value)

    async def api_url(self) -> Optional[str]:
        return self._get_field("api_url")

    async def set_api_url(self, value: Optional[str]) -> None:
        self._set_field("api_url", value)

    async def api_urls(self) -> Optional[list[str]]:
        raw = self._get_field("api_urls_json")
        return json.loads(raw) if raw else None

    async def set_api_urls(self, value: Optional[list[str]]) -> None:
        self._set_field("api_urls_json", json.dumps(value) if value is not None else None)

    async def storages(self) -> Optional[dict[str, str]]:
        raw = self._get_field("storages_json")
        return json.loads(raw) if raw else None

    async def set_storages(self, value: Optional[dict[str, str]]) -> None:
        self._set_field("storages_json", json.dumps(value) if value is not None else None)

    async def cdn_urls(self) -> Optional[dict[str, list[str]]]:
        raw = self._get_field("cdn_urls_json")
        return json.loads(raw) if raw else None

    async def set_cdn_urls(self, value: Optional[dict[str, list[str]]]) -> None:
        self._set_field("cdn_urls_json", json.dumps(value) if value is not None else None)

    async def sockets(self) -> Optional[list[str]]:
        raw = self._get_field("sockets_json")
        return json.loads(raw) if raw else None

    async def set_sockets(self, value: Optional[list[str]]) -> None:
        self._set_field("sockets_json", json.dumps(value) if value is not None else None)

    async def auth(self) -> Optional[str]:
        return self._get_field("auth")

    async def set_auth(self, value: Optional[str]) -> None:
        self._set_field("auth", value)

    async def tmp_session(self) -> Optional[str]:
        return self._get_field("tmp_session")

    async def set_tmp_session(self, value: Optional[str]) -> None:
        self._set_field("tmp_session", value)

    async def public_key(self) -> Optional[str]:
        return self._get_field("public_key")

    async def set_public_key(self, value: Optional[str]) -> None:
        self._set_field("public_key", value)

    async def private_key_pem(self) -> Optional[str]:
        return self._get_field("private_key_pem")

    async def set_private_key_pem(self, value: Optional[str]) -> None:
        self._set_field("private_key_pem", value)

    async def user_guid(self) -> Optional[str]:
        return self._get_field("user_guid")

    async def set_user_guid(self, value: Optional[str]) -> None:
        self._set_field("user_guid", value)

    async def updates_state(self) -> Optional[int]:
        value = self._get_field("updates_state")
        return int(value) if value is not None else None

    async def set_updates_state(self, value: Optional[int]) -> None:
        self._set_field("updates_state", value)

    async def device_hash(self) -> Optional[str]:
        return self._get_field("device_hash")

    async def set_device_hash(self, value: Optional[str]) -> None:
        self._set_field("device_hash", value)

    async def registered_device(self) -> bool:
        return bool(self._get_field("registered_device") or 0)

    async def set_registered_device(self, value: bool) -> None:
        self._set_field("registered_device", 1 if value else 0)

    async def registered_device_version(self) -> Optional[str]:
        return self._get_field("registered_device_version")

    async def set_registered_device_version(self, value: Optional[str]) -> None:
        self._set_field("registered_device_version", value)

    async def bot_token(self) -> Optional[str]:
        return self._get_field("bot_token")

    async def set_bot_token(self, value: Optional[str]) -> None:
        self._set_field("bot_token", value)

    async def bot_offset_id(self) -> Optional[str]:
        return self._get_field("bot_offset_id")

    async def set_bot_offset_id(self, value: Optional[str]) -> None:
        self._set_field("bot_offset_id", value)

    async def export_session_dict(self) -> dict[str, Any]:
        return {
            "api_version": await self.api_version(),
            "api_url": await self.api_url(),
            "api_urls": await self.api_urls(),
            "storages": await self.storages(),
            "cdn_urls": await self.cdn_urls(),
            "sockets": await self.sockets(),
            "auth": await self.auth(),
            "tmp_session": await self.tmp_session(),
            "public_key": await self.public_key(),
            "private_key_pem": await self.private_key_pem(),
            "user_guid": await self.user_guid(),
            "updates_state": await self.updates_state(),
            "device_hash": await self.device_hash(),
            "registered_device": await self.registered_device(),
            "registered_device_version": await self.registered_device_version(),
            "bot_token": await self.bot_token(),
            "bot_offset_id": await self.bot_offset_id(),
        }

    async def export_session_string(self) -> str:
        return dump_session_string(await self.export_session_dict())

    async def import_session_string(self, session_string: str) -> None:
        await self.import_session_dict(load_session_string(session_string))

    async def import_session_dict(self, data: dict[str, Any]) -> None:
        if "api_version" in data:
            await self.set_api_version(str(data["api_version"]))
        if "api_url" in data:
            await self.set_api_url(data["api_url"])
        if "api_urls" in data:
            await self.set_api_urls(data["api_urls"])
        if "storages" in data:
            await self.set_storages(data["storages"])
        if "cdn_urls" in data:
            await self.set_cdn_urls(data["cdn_urls"])
        if "sockets" in data:
            await self.set_sockets(data["sockets"])
        if "auth" in data:
            await self.set_auth(data["auth"])
        if "tmp_session" in data:
            await self.set_tmp_session(data["tmp_session"])
        if "public_key" in data:
            await self.set_public_key(data["public_key"])
        if "private_key_pem" in data:
            await self.set_private_key_pem(data["private_key_pem"])
        if "user_guid" in data:
            await self.set_user_guid(data["user_guid"])
        if "updates_state" in data:
            await self.set_updates_state(data["updates_state"])
        if "device_hash" in data:
            await self.set_device_hash(data["device_hash"])
        if "registered_device" in data:
            await self.set_registered_device(bool(data["registered_device"]))
        if "registered_device_version" in data:
            await self.set_registered_device_version(data["registered_device_version"])
        if "bot_token" in data:
            await self.set_bot_token(data["bot_token"])
        if "bot_offset_id" in data:
            await self.set_bot_offset_id(data["bot_offset_id"])
