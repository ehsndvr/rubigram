"""Bot API message, chat and update models."""

from __future__ import annotations

from typing import Any, Optional

from rubigram.enums.bot import BotChatType, ForwardedFromType, MessageSender, PollStatusState, UpdateType

from ..object import Object, model
from .keypad import AuxData, Keypad, Location


@model
class File(Object):
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    size: Optional[str] = None
    download_url: Optional[str] = None

    async def download(self, path: Any = None, *, in_memory: bool = False) -> Any:
        if self._client is None:
            raise RuntimeError("This file is not bound to a Client instance")
        return await self._client.download_bot_file(self, path=path, in_memory=in_memory)


@model
class Chat(Object):
    chat_id: Optional[str] = None
    chat_type: Optional[BotChatType] = None
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    username: Optional[str] = None


@model
class ForwardedFrom(Object):
    type_from: Optional[ForwardedFromType] = None
    message_id: Optional[str] = None
    from_chat_id: Optional[str] = None
    from_sender_id: Optional[str] = None


@model
class MessageTextUpdate(Object):
    message_id: Optional[str] = None
    text: Optional[str] = None


@model
class BotCommand(Object):
    command: Optional[str] = None
    description: Optional[str] = None


@model
class Bot(Object):
    bot_id: Optional[str] = None
    bot_title: Optional[str] = None
    avatar: Optional[File] = None
    description: Optional[str] = None
    username: Optional[str] = None
    start_message: Optional[str] = None
    share_url: Optional[str] = None


@model
class Sticker(Object):
    sticker_id: Optional[str] = None
    file: Optional[File] = None
    emoji_character: Optional[str] = None


@model
class ContactMessage(Object):
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@model
class PollStatus(Object):
    state: Optional[PollStatusState] = None
    selection_index: Optional[int] = None
    percent_vote_options: list[int] = None  # type: ignore[assignment]
    total_vote: Optional[int] = None
    show_total_votes: Optional[bool] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.percent_vote_options = self.percent_vote_options or []


@model
class Poll(Object):
    question: Optional[str] = None
    options: list[str] = None  # type: ignore[assignment]
    poll_status: Optional[PollStatus] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.options = self.options or []


@model
class Message(Object):
    """A message received by a bot (``new_message`` / ``updated_message``)."""

    message_id: Optional[str] = None
    text: Optional[str] = None
    time: Optional[int] = None
    is_edited: Optional[bool] = None
    sender_type: Optional[MessageSender] = None
    sender_id: Optional[str] = None
    aux_data: Optional[AuxData] = None
    file: Optional[File] = None
    reply_to_message_id: Optional[str] = None
    forwarded_from: Optional[ForwardedFrom] = None
    forwarded_no_link: Optional[str] = None
    location: Optional[Location] = None
    sticker: Optional[Sticker] = None
    contact_message: Optional[ContactMessage] = None
    poll: Optional[Poll] = None
    chat_id: Optional[str] = None
    # Derived fields shared with the user-API Message so the same filters apply.
    type: Optional[str] = None
    chat_type: Optional[str] = None
    is_mine: Optional[bool] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        if self.type is None:
            self.type = self._infer_message_type()
        if self.chat_type is None:
            self.chat_type = self._infer_chat_type()
        if self.is_mine is None:
            self.is_mine = False

    def _infer_message_type(self) -> str:
        if self.poll is not None:
            return "Poll"
        if self.sticker is not None:
            return "Sticker"
        if self.location is not None:
            return "Location"
        if self.contact_message is not None:
            return "Contact"
        if self.file is not None:
            return "File"
        if self.text:
            return "Text"
        return "Unknown"

    def _infer_chat_type(self) -> str:
        if self.sender_type == MessageSender.BOT or self.sender_type == "Bot":
            return BotChatType.BOT.value
        return BotChatType.USER.value

    @property
    def object_guid(self) -> Optional[str]:
        return self.chat_id

    @property
    def author_object_guid(self) -> Optional[str]:
        return self.sender_id

    @property
    def button_id(self) -> Optional[str]:
        return self.aux_data.button_id if self.aux_data is not None else None

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")
        if not self.chat_id:
            raise RuntimeError("This message does not have chat_id")
        return self._client

    async def reply(self, text: str, *, inline_keypad: Optional[Keypad] = None, chat_keypad: Optional[Keypad] = None, chat_keypad_type: Any = None, disable_notification: bool = False, **kwargs: Any) -> Any:
        client = self._require_client()
        return await client.send_message(self.chat_id, text, inline_keypad=inline_keypad, chat_keypad=chat_keypad, chat_keypad_type=chat_keypad_type, disable_notification=disable_notification, reply_to_message_id=self.message_id, **kwargs)

    async def delete(self) -> Any:
        client = self._require_client()
        if not self.message_id:
            raise RuntimeError("This message is missing message_id")
        return await client.delete_message(self.chat_id, self.message_id)

    async def edit_text(self, text: str) -> Any:
        client = self._require_client()
        if not self.message_id:
            raise RuntimeError("This message is missing message_id")
        return await client.edit_message_text(self.chat_id, self.message_id, text)

    edit = edit_text


@model
class InlineMessage(Object):
    """A button interaction delivered to a bot (webhook ``inline_message``)."""

    sender_id: Optional[str] = None
    text: Optional[str] = None
    file: Optional[File] = None
    location: Optional[Location] = None
    aux_data: Optional[AuxData] = None
    message_id: Optional[str] = None
    chat_id: Optional[str] = None

    @property
    def button_id(self) -> Optional[str]:
        return self.aux_data.button_id if self.aux_data is not None else None

    async def answer(self, text: str, **kwargs: Any) -> Any:
        if self._client is None or not self.chat_id:
            raise RuntimeError("This inline message is not bound to a Client instance")
        return await self._client.send_message(self.chat_id, text, **kwargs)


CallbackQuery = InlineMessage


@model
class SentMessage(Object):
    message_id: Optional[str] = None

    @classmethod
    def _parse(cls, client: Any, data: Any) -> Any:
        if data is None:
            return cls(client=client)
        if isinstance(data, cls):
            data.bind(client)
            return data
        if isinstance(data, str):
            return cls(client=client, message_id=data)
        if isinstance(data, dict):
            payload = dict(data)
            message_id = payload.pop("message_id", None) or payload.pop("new_message_id", None)
            instance = cls(client=client, message_id=str(message_id) if message_id is not None else None)
            from ..object import _apply_unknown_fields

            _apply_unknown_fields(instance, client, payload, ())
            return instance
        return cls(client=client)


@model
class Update(Object):
    type: Optional[UpdateType] = None
    chat_id: Optional[str] = None
    removed_message_id: Optional[str] = None
    new_message: Optional[Message] = None
    updated_message: Optional[Message] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        for message in (self.new_message, self.updated_message):
            if message is not None and message.chat_id is None:
                message.chat_id = self.chat_id

    def __post_parse__(self, client: Any, data: dict[str, Any]) -> None:
        for message in (self.new_message, self.updated_message):
            if message is not None and message.chat_id is None:
                message.chat_id = self.chat_id

    @property
    def message(self) -> Optional[Message]:
        return self.new_message or self.updated_message


@model
class BotUpdates(Object):
    updates: list[Update] = None  # type: ignore[assignment]
    next_offset_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.updates = self.updates or []

    def __iter__(self):
        return iter(self.updates)

    def __len__(self) -> int:
        return len(self.updates)


@model
class WebhookUpdate(Object):
    update: Optional[Update] = None
    inline_message: Optional[InlineMessage] = None


__all__ = [
    "File",
    "Chat",
    "ForwardedFrom",
    "MessageTextUpdate",
    "BotCommand",
    "Bot",
    "Sticker",
    "ContactMessage",
    "PollStatus",
    "Poll",
    "Message",
    "InlineMessage",
    "CallbackQuery",
    "SentMessage",
    "Update",
    "BotUpdates",
    "WebhookUpdate",
]
