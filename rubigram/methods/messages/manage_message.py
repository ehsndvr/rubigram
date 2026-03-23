from __future__ import annotations

from typing import Any

import rubigram
from rubigram.bot.types import SentMessage as BotSentMessage
from rubigram.raw.methods import DeleteChatHistory, DeleteMessage, EditMessage, SendChatActivity
from rubigram.types import DeleteChatHistoryResult, Empty, RawObject


class ManageMessage:
    async def send_chat_activity(
        self: "rubigram.Client",
        object_guid: Any = None,
        activity: str = "Typing",
        *,
        peer: Any = None,
    ) -> Empty:
        if self.is_bot:
            raise RuntimeError("send_chat_activity() is only available for authenticated user sessions")
        return await self.invoke(
            SendChatActivity(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                activity=activity,
            )
        )

    async def send_typing(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> Empty:
        return await self.send_chat_activity(object_guid=object_guid, activity="Typing", peer=peer)

    async def edit_message(
        self: "rubigram.Client",
        object_guid: Any = None,
        message_id: str = "",
        text: str = "",
        *,
        peer: Any = None,
    ) -> Any:
        if self.is_bot:
            return BotSentMessage._parse(
                self,
                await self._invoke_bot(
                    "editMessageText",
                    {
                        "chat_id": self._resolve_object_guid(object_guid, peer=peer),
                        "message_id": message_id,
                        "text": text,
                    },
                ),
            )
        return await self.invoke(
            EditMessage(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                message_id=message_id,
                text=text,
            )
        )

    async def delete_message(
        self: "rubigram.Client",
        object_guid: Any = None,
        message_id: str = "",
        *,
        peer: Any = None,
    ) -> Any:
        if self.is_bot:
            await self._invoke_bot(
                "deleteMessage",
                {"chat_id": self._resolve_object_guid(object_guid, peer=peer), "message_id": message_id},
            )
            return True
        return await self.invoke(
            DeleteMessage(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                message_id=message_id,
            )
        )

    async def delete_chat_history(
        self: "rubigram.Client",
        object_guid: Any = None,
        last_message_id: str = "",
        *,
        peer: Any = None,
    ) -> DeleteChatHistoryResult:
        return await self.invoke(
            DeleteChatHistory(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                last_message_id=last_message_id,
            )
        )

    async def edit_message_text(self: "rubigram.Client", chat_id: str, message_id: str, text: str) -> BotSentMessage:
        if not self.is_bot:
            return await self.edit_message(chat_id, message_id=message_id, text=text)
        return BotSentMessage._parse(
            self,
            await self._invoke_bot("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text}),
        )
