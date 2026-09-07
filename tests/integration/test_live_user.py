"""Read-only checks of a logged-in user session (see conftest.py)."""

from __future__ import annotations

import asyncio
import os

import pytest

from rubigram import Client, errors, types

SESSION = os.environ.get("RUBIGRAM_SESSION", "integration")


def test_user_session_read_only_calls():
    async def scenario():
        client = Client(SESSION, interactive=False)
        try:
            await client.start()
        except errors.LoginRequired:
            pytest.skip(f"no logged-in session named {SESSION!r}; log in with examples/user_session.py first")
        try:
            if not await client.storage.auth():
                pytest.skip("session file has no auth; log in first")
            server_time = await client.get_time()
            assert server_time.timestamp
            me = await client.get_me()
            assert isinstance(me, types.UserInfo) and me.user.user_guid
            chats = await client.get_chats()
            assert isinstance(chats, types.ChatsResult)
            updates = await client.get_chats_updates()
            assert isinstance(updates, types.ChatsUpdates)
            async with client.use_transport("ws"):
                try:
                    frame = await asyncio.wait_for(client.receive_update(timeout=5), timeout=8)
                    assert isinstance(frame, types.Updates)
                except (TimeoutError, asyncio.TimeoutError, errors.TransportError):
                    pass  # no push within the window is fine
        finally:
            await client.stop()

    asyncio.run(scenario())
