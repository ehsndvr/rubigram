import asyncio
import base64
import json
import sqlite3

import pytest

from rubigram.errors import StorageError
from rubigram.storage import (
    FIELDS,
    FileStorage,
    MemoryStorage,
    SqliteStorage,
    dump_session_string,
    load_session_string,
    session_string_version,
)
from rubigram.storage.sqlite import SCHEMA_VERSION


def run(coro):
    return asyncio.run(coro)


async def _fill(storage):
    await storage.set_api_urls(["https://messengerg2c513.iranlms.ir"])
    await storage.set_api_url("https://messengerg2c513.iranlms.ir")
    await storage.set_auth("a" * 32)
    await storage.set_tmp_session("b" * 32)
    await storage.set_public_key("public-key")
    await storage.set_private_key_pem("private-key")
    await storage.set_user_guid("u0EXAMPLE00000000000000000000001")
    await storage.set_updates_state(1773595460)
    await storage.set_device_hash("25010064645373614500053736")
    await storage.set_registered_device(True)
    await storage.set_registered_device_version("4.4.34")
    await storage.set_dc_repository({"dcs": {"storages": {"1": "https://messanger.iranlms.ir/GetFile.ashx"}}, "suggested_urls": {}})
    await storage.set_chat_state("g0EXAMPLE00000000000000000000002", 42)


def _assert_filled(storage):
    async def check():
        assert await storage.api_urls() == ["https://messengerg2c513.iranlms.ir"]
        assert await storage.api_url() == "https://messengerg2c513.iranlms.ir"
        assert await storage.auth() == "a" * 32
        assert await storage.tmp_session() == "b" * 32
        assert await storage.public_key() == "public-key"
        assert await storage.private_key_pem() == "private-key"
        assert await storage.user_guid() == "u0EXAMPLE00000000000000000000001"
        assert await storage.updates_state() == 1773595460
        assert await storage.device_hash() == "25010064645373614500053736"
        assert await storage.registered_device() is True
        assert await storage.registered_device_version() == "4.4.34"
        assert (await storage.dc_repository())["dcs"]["storages"]["1"].endswith("GetFile.ashx")
        assert await storage.chat_state("g0EXAMPLE00000000000000000000002") == 42
        assert await storage.api_version() == "6"

    run(check())


def test_file_storage_round_trips_through_v2_session_string(tmp_path):
    async def scenario():
        file_storage = FileStorage("test_account", tmp_path)
        await file_storage.open()
        await _fill(file_storage)
        session_string = await file_storage.export_session_string()
        await file_storage.close()
        assert session_string.startswith("rbg2.")
        assert session_string_version(session_string) == 2
        memory = MemoryStorage("memory_account", session_string)
        await memory.open()
        return memory

    memory = run(scenario())
    _assert_filled(memory)


def test_legacy_base64_json_session_string_still_loads():
    legacy = base64.urlsafe_b64encode(json.dumps({"auth": "x" * 32, "api_version": "6", "user_guid": "u1"}).encode()).decode().rstrip("=")
    assert session_string_version(legacy) == 1
    data = load_session_string(legacy)
    assert data["auth"] == "x" * 32
    memory = MemoryStorage("legacy", legacy)
    run(memory.open())
    assert run(memory.auth()) == "x" * 32
    assert run(memory.user_guid()) == "u1"


def test_corrupt_session_strings_raise_storage_error():
    with pytest.raises(StorageError):
        load_session_string("")
    with pytest.raises(StorageError):
        load_session_string("rbg2.not-base64!!")
    good = dump_session_string({"auth": "abc"})
    with pytest.raises(StorageError):
        load_session_string(good[:-3] + "AAA")
    with pytest.raises(StorageError):
        load_session_string(base64.urlsafe_b64encode(b"[1, 2]").decode())


def test_memory_storage_keeps_state_across_close_and_open():
    async def scenario():
        storage = MemoryStorage("mem")
        with pytest.raises(StorageError):
            await storage.auth()
        await storage.open()
        await storage.set_auth("auth-1")
        await storage.close()
        assert not storage.is_open
        await storage.open()
        assert await storage.auth() == "auth-1"
        await storage.clear_auth()
        assert await storage.auth() is None
        assert await storage.registered_device() is False
        await storage.delete()
        assert await storage.api_version() == "6"

    run(scenario())


def test_sqlite_storage_migrates_the_rubigram_0_1_schema(tmp_path):
    database = tmp_path / "old.session"
    conn = sqlite3.connect(database)
    conn.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE session (
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
        INSERT INTO meta VALUES ('version', '1');
        INSERT INTO session (id, api_version, auth, user_guid, registered_device, created_at, updated_at)
        VALUES (1, '6', 'old-auth', 'u0EXAMPLE00000000000000000000001', 1, 1, 1);
        """
    )
    conn.commit()
    conn.close()

    async def scenario():
        storage = SqliteStorage("old", tmp_path)
        await storage.open()
        assert await storage.auth() == "old-auth"
        assert await storage.user_guid() == "u0EXAMPLE00000000000000000000001"
        assert await storage.bot_token() is None
        assert await storage.dc_repository() is None
        await storage.set_bot_token("token")
        await storage.set_chat_state("c0EXAMPLE00000000000000000000003", 7)
        assert storage.schema_version() == SCHEMA_VERSION
        assert storage.conn is not None
        columns = {row[1] for row in storage.conn.execute("PRAGMA table_info(session)").fetchall()}
        assert {field.column for field in FIELDS} <= columns
        await storage.close()
        reopened = SqliteStorage("old", tmp_path)
        await reopened.open()
        assert await reopened.bot_token() == "token"
        assert await reopened.chat_state("c0EXAMPLE00000000000000000000003") == 7
        await reopened.delete()
        assert not database.exists()

    run(scenario())


def test_sqlite_storage_requires_open_and_creates_parent_dirs(tmp_path):
    async def scenario():
        storage = SqliteStorage("fresh", tmp_path / "nested" / "dir")
        with pytest.raises(StorageError):
            await storage.auth()
        await storage.open()
        assert storage.database.exists()
        await storage.set_auth(None)
        assert await storage.auth() is None
        exported = await storage.export_session_dict()
        assert set(exported) == {field.name for field in FIELDS}
        await storage.close()

    run(scenario())


def test_export_import_dict_is_lossless():
    async def scenario():
        source = MemoryStorage("a")
        await source.open()
        await _fill(source)
        data = await source.export_session_dict()
        target = MemoryStorage("b")
        await target.open()
        await target.import_session_dict(data)
        return target

    _assert_filled(run(scenario()))
