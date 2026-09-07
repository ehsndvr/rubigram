"""Read-only checks of a bot token (see conftest.py)."""

from __future__ import annotations

import asyncio
import os

import pytest

from rubigram import Client, types


def test_bot_get_me_and_updates():
    token = os.environ.get("RUBIGRAM_BOT_TOKEN")
    if not token:
        pytest.skip("RUBIGRAM_BOT_TOKEN is not set")

    async def scenario():
        async with Client("integration_bot", token=token, in_memory=True) as bot:
            me = await bot.get_me()
            assert isinstance(me, types.bot.Bot) and me.bot_id
            updates = await bot.get_updates(limit=1)
            assert isinstance(updates, types.bot.BotUpdates)

    asyncio.run(scenario())
