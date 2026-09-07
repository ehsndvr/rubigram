"""Message models and the message update envelope."""

from __future__ import annotations

import time
from typing import Any, Optional

from .files import FileInline, Sticker
from .object import Object, model
from .raw_object import RawObject


@model
class ForwardedFrom(Object):
    type_from: Optional[str] = None
    message_id: Optional[str] = None
    object_guid: Optional[str] = None
    forwarded_from_type: Optional[str] = None


@model
class RubinoPostData(Object):
    post_id: Optional[str] = None
    post_profile_id: Optional[str] = None
    track_id: Optional[str] = None


@model
class LiveStatus(Object):
    status: Optional[str] = None
    play_count: Optional[int] = None
    allow_comment: Optional[bool] = None
    can_play: Optional[bool] = None
    timestamp: Optional[str] = None
    title: Optional[str] = None


@model
class LiveData(Object):
    live_id: Optional[str] = None
    thumb_inline: Optional[str] = None
    access_token: Optional[str] = None
    title: Optional[str] = None
    live_status: Optional[LiveStatus] = None


@model
class Location(Object):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_view: Optional[Any] = None


@model
class ContactMessage(Object):
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_guid: Optional[str] = None
    vcard: Optional[str] = None


@model
class MetadataPart(Object):
    type: Optional[str] = None
    from_index: Optional[int] = None
    length: Optional[int] = None
    mention_text_object_guid: Optional[str] = None
    mention_text_object_type: Optional[str] = None
    link: Optional[Any] = None


@model
class MessageMetadata(Object):
    meta_data_parts: list[MetadataPart] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.meta_data_parts = self.meta_data_parts or []


@model
class EventData(Object):
    type: Optional[str] = None
    performer_object: Optional[Any] = None
    peer_objects: list[Any] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.peer_objects = self.peer_objects or []


@model
class ReactionCount(Object):
    reaction_id: Optional[int] = None
    emoji_char: Optional[str] = None
    reaction_count: Optional[int] = None
    is_selected: Optional[bool] = None


@model
class Message(Object):
    """A chat message (also the payload of socket ``message_updates``).

    The update-envelope fields ``action``, ``chat_type``, ``state``,
    ``is_scheduled`` and ``prev_message_id`` are copied down from
    :class:`MessageUpdate` so filters can work on the message alone.
    """

    message_id: Optional[str] = None
    type: Optional[str] = None
    text: Optional[str] = None
    time: Optional[int] = None
    is_edited: Optional[bool] = None
    author_object_guid: Optional[str] = None
    author_type: Optional[str] = None
    is_mine: Optional[bool] = None
    object_guid: Optional[str] = None
    reply_to_message_id: Optional[str] = None
    forwarded_from: Optional[ForwardedFrom] = None
    forwarded_no_link: Optional[bool] = None
    file_inline: Optional[FileInline] = None
    sticker: Optional[Sticker] = None
    rubino_post_data: Optional[RubinoPostData] = None
    live_data: Optional[LiveData] = None
    location: Optional[Location] = None
    contact_message: Optional[ContactMessage] = None
    metadata: Optional[MessageMetadata] = None
    event_data: Optional[EventData] = None
    reactions: list[ReactionCount] = None  # type: ignore[assignment]
    count_seen: Optional[int] = None
    allow_transcription: Optional[bool] = None
    auto_delete: Optional[int] = None
    # Envelope fields copied from the update.
    action: Optional[str] = None
    chat_type: Optional[str] = None
    state: Optional[str] = None
    is_scheduled: Optional[bool] = None
    prev_message_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        if self.reactions is None:
            self.reactions = []

    # -- convenience --------------------------------------------------------

    @property
    def chat_id(self) -> Optional[str]:
        return self.object_guid

    @property
    def media(self) -> Optional[FileInline]:
        return self.file_inline

    @property
    def is_media(self) -> bool:
        return self.file_inline is not None or self.sticker is not None

    @property
    def caption(self) -> Optional[str]:
        return self.text if self.file_inline is not None else None

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")
        if not self.object_guid:
            raise RuntimeError("This message does not have object_guid")
        return self._client

    async def reply(self, text: str, parse_mode: Any = None, entities: Optional[list[Any]] = None, **kwargs: Any) -> Any:
        """Send ``text`` in this chat as a reply to this message."""
        client = self._require_client()
        if not self.message_id:
            raise RuntimeError("This message does not have message_id required for reply()")
        return await client.send_message(
            object_guid=self.object_guid,
            rnd=str(time.time_ns()),
            text=text,
            parse_mode=parse_mode,
            entities=entities,
            reply_to_message_id=self.message_id,
            **kwargs,
        )

    async def edit(self, text: str, parse_mode: Any = None, entities: Optional[list[Any]] = None) -> Any:
        client = self._require_client()
        return await client.edit_message(self.object_guid, self.message_id, text, parse_mode=parse_mode, entities=entities)

    async def delete(self, *, delete_type: Any = "Global") -> Any:
        client = self._require_client()
        return await client.delete_messages(self.object_guid, [self.message_id], delete_type=delete_type)

    async def forward(self, to_object_guid: Any) -> Any:
        client = self._require_client()
        return await client.forward_messages(self.object_guid, to_object_guid, [self.message_id])

    async def pin(self) -> Any:
        client = self._require_client()
        return await client.pin_message(self.object_guid, self.message_id)

    async def unpin(self) -> Any:
        client = self._require_client()
        return await client.unpin_message(self.object_guid, self.message_id)

    async def react(self, reaction_id: Any) -> Any:
        client = self._require_client()
        return await client.react(self.object_guid, self.message_id, reaction_id)

    async def unreact(self, reaction_id: Any) -> Any:
        client = self._require_client()
        return await client.unreact(self.object_guid, self.message_id, reaction_id)

    async def seen(self) -> Any:
        client = self._require_client()
        return await client.seen_chats({self.object_guid: self.message_id})

    async def download(
        self,
        path: Any = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        """Download the message media (file, sticker) through the bound client."""
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")
        return await self._client.download_file(
            self, path=path, in_memory=in_memory, file_name=file_name, progress=progress, progress_args=progress_args
        )


@model
class MessageUpdate(Object):
    """One entry of ``message_updates`` (socket push or RPC result)."""

    message_id: Optional[str] = None
    action: Optional[str] = None
    message: Optional[Message] = None
    updated_parameters: list[str] = None  # type: ignore[assignment]
    timestamp: Optional[str] = None
    prev_message_id: Optional[str] = None
    object_guid: Optional[str] = None
    type: Optional[str] = None
    state: Optional[str] = None
    is_scheduled: Optional[bool] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        if self.updated_parameters is None:
            self.updated_parameters = []
        self._sync_message()

    def __post_parse__(self, client: Any, data: dict[str, Any]) -> None:
        self._sync_message()

    def _sync_message(self) -> None:
        message = self.message
        if message is None:
            return
        message.action = self.action
        message.chat_type = self.type
        message.state = self.state
        message.is_scheduled = self.is_scheduled
        message.prev_message_id = self.prev_message_id
        if message.object_guid is None:
            message.object_guid = self.object_guid
        if message.message_id is None:
            message.message_id = self.message_id


SocketMessageUpdate = MessageUpdate

__all__ = [
    "ContactMessage",
    "EventData",
    "ForwardedFrom",
    "LiveData",
    "LiveStatus",
    "Location",
    "Message",
    "MessageMetadata",
    "MessageUpdate",
    "MetadataPart",
    "RawObject",
    "ReactionCount",
    "RubinoPostData",
    "SocketMessageUpdate",
]
