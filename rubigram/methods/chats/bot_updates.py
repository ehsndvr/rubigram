from __future__ import annotations

from typing import Optional

import asyncio
import rubigram
from rubigram.bot.types import BotUpdates


class BotUpdatesMethods:
    async def get_updates(self: "rubigram.Client", offset_id: Optional[str] = None, limit: Optional[int] = None) -> BotUpdates:
        if not self.is_bot:
            raise RuntimeError("get_updates() is only available for token-based bot sessions")
        payload = self._clean_bot_payload({"offset_id": offset_id or self._bot_last_offset_id, "limit": limit})
        result = BotUpdates._parse(self, await self._invoke_bot("getUpdates", payload))
        if result.next_offset_id is not None:
            self._bot_last_offset_id = result.next_offset_id
            await self.storage.set_bot_offset_id(result.next_offset_id)
        return result

    async def start_polling(self: "rubigram.Client", *, limit: int = 100, idle_sleep: float = 1.0) -> None:
        if not self.is_bot:
            raise RuntimeError("start_polling() is only available for token-based bot sessions")
        if self._bot_polling_task is not None and not self._bot_polling_task.done():
            return
        self._bot_polling_stop.clear()
        self._bot_polling_task = asyncio.create_task(self._bot_polling_loop(limit=limit, idle_sleep=idle_sleep))

    async def stop_polling(self: "rubigram.Client") -> None:
        self._bot_polling_stop.set()
        if self._bot_polling_task is not None:
            self._bot_polling_task.cancel()
            try:
                await self._bot_polling_task
            except asyncio.CancelledError:
                pass
            self._bot_polling_task = None

    async def parse_webhook_update(self: "rubigram.Client", payload: dict[str, object]):
        if not self.is_bot:
            raise RuntimeError("parse_webhook_update() is only available for token-based bot sessions")
        from rubigram.bot.types import WebhookUpdate

        return WebhookUpdate._parse(self, payload)

    async def dispatch_webhook_update(self: "rubigram.Client", payload: dict[str, object]):
        update = await self.parse_webhook_update(payload)
        if update.update is not None:
            await self._dispatch_bot_update(update.update)
        if update.inline_message is not None:
            for handler in list(self._inline_message_handlers):
                result = handler(self, update.inline_message)
                if asyncio.iscoroutine(result):
                    await result
        return update
