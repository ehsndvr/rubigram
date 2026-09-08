"""Channel models and results."""

from __future__ import annotations

from typing import Any, Optional

from .chat import Chat, ChatUpdate
from .files import AvatarThumbnail
from .group import ChatReactionSetting, GroupMember
from .message import MessageUpdate
from .object import Object, model


@model
class Channel(Object):
    channel_guid: Optional[str] = None
    channel_title: Optional[str] = None
    avatar_thumbnail: Optional[AvatarThumbnail] = None
    count_members: Optional[int] = None
    description: Optional[str] = None
    username: Optional[str] = None
    is_deleted: Optional[bool] = None
    is_verified: Optional[bool] = None
    channel_type: Optional[str] = None
    sign_messages: Optional[bool] = None
    chat_reaction_setting: Optional[ChatReactionSetting] = None
    is_restricted_content: Optional[bool] = None
    share_url: Optional[str] = None

    @property
    def title(self) -> Optional[str]:
        return self.channel_title

    async def leave(self) -> Any:
        if self._client is None or not self.channel_guid:
            raise RuntimeError("This channel is not bound to a Client instance")
        return await self._client.leave_channel(self.channel_guid)


@model
class ChannelInfo(Object):
    channel: Optional[Channel] = None
    chat: Optional[Chat] = None
    timestamp: Optional[str] = None


@model
class AddChannelResult(Object):
    channel: Optional[Channel] = None
    chat_update: Optional[ChatUpdate] = None
    message_update: Optional[MessageUpdate] = None
    timestamp: Optional[str] = None


@model
class AddChannelMembersResult(Object):
    added_in_chat_members: list[GroupMember] = None  # type: ignore[assignment]
    timestamp: Optional[str] = None
    channel: Optional[Channel] = None
    chat_update: Optional[ChatUpdate] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.added_in_chat_members = self.added_in_chat_members or []


@model
class EditChannelInfoResult(Object):
    channel: Optional[Channel] = None
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None


@model
class BanChannelMemberResult(Object):
    channel: Optional[Channel] = None
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None


@model
class ChannelLink(Object):
    join_link: Optional[str] = None


@model
class ChannelPreview(Object):
    """Result of ``channelPreviewByJoinLink``."""

    is_valid: Optional[bool] = None
    channel: Optional[Channel] = None
    is_member: Optional[bool] = None
    timestamp: Optional[str] = None


@model
class JoinedChannel(Object):
    """Result of ``joinChannelAction`` / ``joinChannelByLink``."""

    channel: Optional[Channel] = None
    chat_update: Optional[ChatUpdate] = None
    message_update: Optional[MessageUpdate] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None


__all__ = [
    "AddChannelMembersResult",
    "AddChannelResult",
    "BanChannelMemberResult",
    "Channel",
    "ChannelInfo",
    "ChannelLink",
    "ChannelPreview",
    "EditChannelInfoResult",
    "JoinedChannel",
]
