from typing import Any, Dict, Optional, Sequence

import rubigram
from rubigram.enums import ParseMode
from rubigram.raw import methods
from rubigram.types import MessageEntity, SentMessage


class SendMessage:
    async def send_message(
        self: "rubigram.Client",
        object_guid: str | Any = None,
        rnd: str | None = None,
        text: Optional[str] = None,
        parse_mode: Optional[str | ParseMode] = None,
        reply_to_message_id: Optional[str] = None,
        file_inline: Optional[Dict[str, Any]] = None,
        entities: Optional[Sequence[MessageEntity]] = None,
        *,
        peer: Any = None,
        chat_keypad: Any = None,
        disable_notification: bool = False,
        inline_keypad: Any = None,
        chat_keypad_type: Any = None,
    ) -> SentMessage:
        if self.is_bot:
            if text is None and isinstance(rnd, str):
                text = rnd
                rnd = None
            if text is None:
                raise ValueError("Bot send_message() requires text")
            return await self._send_bot_message(
                chat_id=self._resolve_object_guid(object_guid, peer=peer),
                text=text,
                chat_keypad=chat_keypad,
                disable_notification=disable_notification,
                inline_keypad=inline_keypad,
                reply_to_message_id=reply_to_message_id,
                chat_keypad_type=chat_keypad_type,
            )
        if rnd is None:
            raise ValueError("rnd is required")
        resolved_text, metadata = self._build_message_metadata(
            text, entities=entities, parse_mode=parse_mode)
        return await self.invoke(
            methods.SendMessage(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                rnd=rnd,
                text=resolved_text,
                file_inline=file_inline,
                metadata=metadata,
                parse_mode=None,
                reply_to_message_id=reply_to_message_id,
            )
        )
