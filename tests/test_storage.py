import asyncio
import shutil
import uuid
from pathlib import Path

from rubigram.storage import FileStorage, MemoryStorage


def test_file_and_memory_storage_share_session_string_format():
    async def scenario():
        workspace_tmp = Path.cwd() / "_test_storage_tmp"
        workspace_tmp.mkdir(exist_ok=True)
        tempdir = workspace_tmp / f"storage-{uuid.uuid4().hex}"
        tempdir.mkdir()

        try:
            file_storage = FileStorage("test_account", tempdir)
            await file_storage.open()
            await file_storage.set_api_urls(["https://messengerg2c513.iranlms.ir"])
            await file_storage.set_api_url("https://messengerg2c513.iranlms.ir")
            await file_storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")
            await file_storage.set_tmp_session("abcdefghijklmnopqrstuvwxyzabcdef")
            await file_storage.set_public_key("public-key")
            await file_storage.set_private_key_pem("private-key")
            await file_storage.set_user_guid("u-test")
            await file_storage.set_device_hash("25010064645373614500053736")
            await file_storage.set_registered_device(True)
            await file_storage.set_registered_device_version("4.4.27")

            session_string = await file_storage.export_session_string()
            await file_storage.close()

            memory_storage = MemoryStorage("memory_account", session_string)
            await memory_storage.open()

            assert await memory_storage.api_urls() == ["https://messengerg2c513.iranlms.ir"]
            assert await memory_storage.api_url() == "https://messengerg2c513.iranlms.ir"
            assert await memory_storage.auth() == "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
            assert await memory_storage.tmp_session() == "abcdefghijklmnopqrstuvwxyzabcdef"
            assert await memory_storage.public_key() == "public-key"
            assert await memory_storage.private_key_pem() == "private-key"
            assert await memory_storage.user_guid() == "u-test"
            assert await memory_storage.device_hash() == "25010064645373614500053736"
            assert await memory_storage.registered_device() is True
            assert await memory_storage.registered_device_version() == "4.4.27"

            await memory_storage.close()
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)
            shutil.rmtree(workspace_tmp, ignore_errors=True)

    asyncio.run(scenario())
