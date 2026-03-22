from __future__ import annotations

from typing import Any, Optional

import rubigram
from rubigram.raw.methods import GetChat, GetChatsUpdates, GetHistory, GetMessages
from rubigram.types import ChatsUpdates, RawObject
from rubigram.bot.types import BotUpdates, Chat as BotChat


class Dialogs:
    async def get_chat(self: "rubigram.Client", object_guid: Any = None, *, peer: Any = None) -> Any:
        if self.is_bot:
            data = await self._invoke_bot("getChat", {"chat_id": self._resolve_object_guid(object_guid, peer=peer)})
            if isinstance(data, dict) and "chat" in data:
                data = data["chat"]
            return BotChat._parse(self, data)
        return await self.invoke(GetChat(object_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_messages(
        self: "rubigram.Client",
        object_guid: Any = None,
        offset: int = 0,
        limit: int = 20,
        *,
        peer: Any = None,
    ) -> RawObject:
        return await self.invoke(
            GetMessages(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                offset=offset,
                limit=limit,
            )
        )

    async def get_history(
        self: "rubigram.Client",
        object_guid: Any = None,
        offset: int = 0,
        limit: int = 50,
        *,
        peer: Any = None,
    ) -> RawObject:
        return await self.invoke(
            GetHistory(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                offset=offset,
                limit=limit,
            )
        )

    async def get_chats_updates(self: "rubigram.Client", state: Optional[int] = None) -> ChatsUpdates:
        if state is None:
            state = await self.storage.updates_state()
        if state is None:
            import time

            state = int(time.time())

        result = await self.invoke(GetChatsUpdates(state=state))
        if result.new_state is not None:
            await self.storage.set_updates_state(result.new_state)
        return result
