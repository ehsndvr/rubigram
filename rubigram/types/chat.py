"""Chat (dialog) models and message-level results that carry chat updates."""

from __future__ import annotations

from typing import Any, Optional

from .files import AvatarThumbnail
from .message import Message, MessageUpdate
from .object import Object, model
from .user import PeerObject

_GUID_PREFIXES = {"u0": "User", "g0": "Group", "c0": "Channel", "b0": "Bot", "s0": "Service"}


def chat_type_from_guid(object_guid: Optional[str]) -> Optional[str]:
    """Infer ``User``/``Group``/``Channel``/``Bot``/``Service`` from the guid prefix."""
    if not object_guid:
        return None
    return _GUID_PREFIXES.get(str(object_guid)[:2])


@model
class Chat(Object):
    """A dialog entry as returned by ``getChats`` / ``getChatsUpdates``."""

    object_guid: Optional[str] = None
    access: list[str] = None  # type: ignore[assignment]
    count_unseen: Optional[int] = None
    is_mute: Optional[bool] = None
    is_pinned: Optional[bool] = None
    time_string: Optional[str] = None
    last_message: Optional[Message] = None
    last_seen_my_mid: Optional[str] = None
    last_seen_peer_mid: Optional[str] = None
    status: Optional[str] = None
    time: Optional[int] = None
    avatar_thumbnail: Optional[AvatarThumbnail] = None
    abs_object: Optional[PeerObject] = None
    is_blocked: Optional[bool] = None
    last_message_id: Optional[str] = None
    last_deleted_mid: Optional[str] = None
    is_in_contact: Optional[bool] = None
    show_ask_spam: Optional[bool] = None
    auto_delete: Optional[str] = None
    pinned_message_id: Optional[str] = None
    is_archived: Optional[bool] = None
    slow_mode_duration: Optional[int] = None
    group_my_last_send_time: Optional[int] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        if self.access is None:
            self.access = []
        if self.last_message is not None and self.last_message.object_guid is None:
            self.last_message.object_guid = self.object_guid

    def __post_parse__(self, client: Any, data: dict[str, Any]) -> None:
        if self.last_message is not None and self.last_message.object_guid is None:
            self.last_message.object_guid = self.object_guid

    @property
    def type(self) -> Optional[str]:
        if self.abs_object is not None and self.abs_object.type:
            return self.abs_object.type
        if self.extra.get("type"):
            return str(self.extra["type"])
        return chat_type_from_guid(self.object_guid)

    @property
    def title(self) -> Optional[str]:
        return self.abs_object.display_name if self.abs_object is not None else None

    def _require_client(self) -> Any:
        if self._client is None or not self.object_guid:
            raise RuntimeError("This chat is not bound to a Client instance")
        return self._client

    async def send_message(self, text: str, **kwargs: Any) -> Any:
        return await self._require_client().send_message(self.object_guid, text=text, **kwargs)

    async def get_messages(self, **kwargs: Any) -> Any:
        return await self._require_client().get_messages(self.object_guid, **kwargs)

    async def seen(self, message_id: Optional[str] = None) -> Any:
        return await self._require_client().seen_chats({self.object_guid: message_id or self.last_message_id})

    async def mute(self) -> Any:
        return await self._require_client().set_action_chat(self.object_guid, "Mute")

    async def unmute(self) -> Any:
        return await self._require_client().set_action_chat(self.object_guid, "Unmute")

    async def pin(self) -> Any:
        return await self._require_client().set_action_chat(self.object_guid, "Pin")

    async def unpin(self) -> Any:
        return await self._require_client().set_action_chat(self.object_guid, "Unpin")

    async def delete_history(self, last_message_id: Optional[str] = None) -> Any:
        return await self._require_client().delete_chat_history(self.object_guid, last_message_id or self.last_message_id)


@model
class ChatUpdate(Object):
    """One entry of ``chat_updates``."""

    object_guid: Optional[str] = None
    action: Optional[str] = None
    chat: Optional[Chat] = None
    updated_parameters: list[str] = None  # type: ignore[assignment]
    timestamp: Optional[str] = None
    type: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        if self.updated_parameters is None:
            self.updated_parameters = []
        self._sync_chat()

    def __post_parse__(self, client: Any, data: dict[str, Any]) -> None:
        self._sync_chat()

    def _sync_chat(self) -> None:
        chat = self.chat
        if chat is None:
            return
        if chat.object_guid is None:
            chat.object_guid = self.object_guid
        if chat.last_message is not None and chat.last_message.object_guid is None:
            chat.last_message.object_guid = chat.object_guid


SocketChatUpdate = ChatUpdate


@model
class ChatsResult(Object):
    """Result of ``getChats`` / ``getChatsByID``."""

    chats: list[Chat] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None
    state: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.chats = self.chats or []

    def __iter__(self):
        return iter(self.chats)

    def __len__(self) -> int:
        return len(self.chats)


@model
class ChatsUpdates(Object):
    """Result of ``getChatsUpdates``; ``status == "OldState"`` means reload."""

    chats: list[Chat] = None  # type: ignore[assignment]
    deleted_chats: list[str] = None  # type: ignore[assignment]
    new_state: Optional[int] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.chats = self.chats or []
        self.deleted_chats = self.deleted_chats or []

    @property
    def is_old_state(self) -> bool:
        return self.status == "OldState"


@model
class SentMessage(Object):
    """Result of ``sendMessage`` / ``editMessage`` / ``setPinMessage`` … ."""

    message_update: Optional[MessageUpdate] = None
    status: Optional[str] = None
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None

    @property
    def message(self) -> Optional[Message]:
        return self.message_update.message if self.message_update is not None else None

    @property
    def message_id(self) -> Optional[str]:
        if self.message_update is None:
            return None
        return self.message_update.message_id or (self.message.message_id if self.message else None)


@model
class ForwardedMessages(Object):
    """Result of ``forwardMessages`` / ``sendMessageAPICall``."""

    message_updates: list[MessageUpdate] = None  # type: ignore[assignment]
    chat_update: Optional[ChatUpdate] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.message_updates = self.message_updates or []


@model
class DeletedMessages(Object):
    """Result of ``deleteMessages``."""

    message_updates: list[MessageUpdate] = None  # type: ignore[assignment]
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.message_updates = self.message_updates or []


@model
class DeleteChatHistoryResult(Object):
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None


@model
class MessagesResult(Object):
    """Result of ``getMessages`` / ``getMessagesByID`` / ``getMessagesInterval``."""

    messages: list[Message] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    new_min_id: Optional[str] = None
    new_max_id: Optional[str] = None
    state: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.messages = self.messages or []

    def __iter__(self):
        return iter(self.messages)

    def __len__(self) -> int:
        return len(self.messages)


@model
class MessagesUpdates(Object):
    """Result of ``getMessagesUpdates``; ``status == "OldState"`` means reload."""

    updated_messages: list[Message] = None  # type: ignore[assignment]
    new_state: Optional[int] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.updated_messages = self.updated_messages or []

    @property
    def is_old_state(self) -> bool:
        return self.status == "OldState"


@model
class SearchMessagesResult(Object):
    """Result of ``searchChatMessages`` / ``searchGlobalMessages``."""

    messages: list[Message] = None  # type: ignore[assignment]
    message_ids: list[str] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.messages = self.messages or []
        self.message_ids = self.message_ids or []


@model
class MessageReadParticipants(Object):
    participants: list[PeerObject] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.participants = self.participants or []


@model
class ChatAdsResult(Object):
    chat_ads: list[Any] = None  # type: ignore[assignment]
    new_state: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.chat_ads = self.chat_ads or []


@model
class ShareUrl(Object):
    share_url: Optional[str] = None


__all__ = [
    "Chat",
    "ChatAdsResult",
    "ChatUpdate",
    "ChatsResult",
    "ChatsUpdates",
    "DeleteChatHistoryResult",
    "DeletedMessages",
    "ForwardedMessages",
    "MessageReadParticipants",
    "MessagesResult",
    "MessagesUpdates",
    "SearchMessagesResult",
    "SentMessage",
    "ShareUrl",
    "SocketChatUpdate",
]
