from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

import rubigram
from rubigram.enums import ParseMode
from rubigram.raw import methods
from rubigram.types import MessageEntity, SentMessage


class SendMessage:
    async def send_message(
        self: "rubigram.Client",
        object_guid: str,
        rnd: str,
        text: Optional[str] = None,
        parse_mode: Optional[str | ParseMode] = None,
        reply_to_message_id: Optional[str] = None,
        file_inline: Optional[Dict[str, Any]] = None,
        entities: Optional[Sequence[MessageEntity]] = None,
    ) -> SentMessage:
        resolved_text, metadata = self._build_message_metadata(
            text, entities=entities, parse_mode=parse_mode)
        return await self.invoke(
            methods.SendMessage(
                object_guid=object_guid,
                rnd=rnd,
                text=resolved_text,
                file_inline=file_inline,
                metadata=metadata,
                parse_mode=None,
                reply_to_message_id=reply_to_message_id,
            )
        )
