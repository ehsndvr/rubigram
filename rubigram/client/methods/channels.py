"""Channels: info, members, admins, links, username, join/leave."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence

from rubigram.raw.functions import build_updated_parameters
from rubigram.raw.methods import (
    AddChannel,
    AddChannelMembers,
    BanChannelMember,
    ChannelPreviewByJoinLink,
    CheckChannelUsername,
    EditChannelInfo,
    GetBannedChannelMembers,
    GetChannelAdminAccessList,
    GetChannelAdminMembers,
    GetChannelAllMembers,
    GetChannelInfo,
    GetChannelLink,
    JoinChannelAction,
    JoinChannelByLink,
    RemoveChannel,
    SetChannelAdmin,
    SetChannelLink,
    UpdateChannelUsername,
)
from rubigram.types import (
    AddChannelMembersResult,
    AddChannelResult,
    AdminAccessList,
    BanChannelMemberResult,
    ChannelInfo,
    ChannelLink,
    ChannelPreview,
    EditChannelInfoResult,
    GroupMembers,
    JoinedChannel,
    RawObject,
    SetGroupAdminResult,
    UsernameCheck,
)

from .groups import _hash_link

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client

_EDITABLE = ("title", "description", "channel_type", "sign_messages", "chat_reaction_setting")


class Channels:
    async def add_channel(
        self: "Client",
        title: str,
        description: str = "",
        channel_type: Any = "Private",
        member_guids: Sequence[Any] | None = None,
        *,
        thumbnail_file_id: Optional[str] = None,
        main_file_id: Optional[str] = None,
    ) -> AddChannelResult:
        """Create a channel (``addChannel``); avatar ids are optional. [HTTP]"""
        return await self.invoke(
            AddChannel(
                title=title,
                description=description or None,
                channel_type=str(getattr(channel_type, "value", channel_type)),
                member_guids=self._resolve_guids(member_guids),
                thumbnail_file_id=thumbnail_file_id,
                main_file_id=main_file_id,
            )
        )

    create_channel = add_channel

    async def get_channel_info(self: "Client", object_guid: Any = None, *, peer: Any = None) -> ChannelInfo:
        """``getChannelInfo``. [HTTP]"""
        return await self.invoke(GetChannelInfo(channel_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def edit_channel_info(
        self: "Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        channel_type: Optional[Any] = None,
        sign_messages: Optional[bool] = None,
        chat_reaction_setting: Optional[Dict[str, Any]] = None,
    ) -> EditChannelInfoResult:
        """Change channel settings (``editChannelInfo``); only the given fields are sent. [HTTP]"""
        values, names = build_updated_parameters(
            {"title": title, "description": description, "channel_type": channel_type, "sign_messages": sign_messages, "chat_reaction_setting": chat_reaction_setting},
            allowed=_EDITABLE,
        )
        if not names:
            raise ValueError("At least one supported channel field must be provided")
        return await self.invoke(EditChannelInfo(channel_guid=self._resolve_object_guid(object_guid, peer=peer), updated_parameters=names, **values))

    async def add_channel_members(self: "Client", object_guid: Any = None, member_guids: Sequence[Any] | None = None, *, peer: Any = None) -> AddChannelMembersResult:
        return await self.invoke(AddChannelMembers(channel_guid=self._resolve_object_guid(object_guid, peer=peer), member_guids=self._resolve_guids(member_guids)))

    async def get_channel_all_members(self: "Client", object_guid: Any = None, *, peer: Any = None, start_id: Optional[str] = None, search_text: Optional[str] = None) -> GroupMembers:
        return await self.invoke(GetChannelAllMembers(channel_guid=self._resolve_object_guid(object_guid, peer=peer), start_id=start_id, search_text=search_text))

    async def get_channel_admin_members(self: "Client", object_guid: Any = None, *, peer: Any = None, start_id: Optional[str] = None, search_text: Optional[str] = None) -> GroupMembers:
        return await self.invoke(GetChannelAdminMembers(channel_guid=self._resolve_object_guid(object_guid, peer=peer), start_id=start_id, search_text=search_text))

    async def get_banned_channel_members(self: "Client", object_guid: Any = None, *, peer: Any = None, start_id: Optional[str] = None, search_text: Optional[str] = None) -> GroupMembers:
        return await self.invoke(GetBannedChannelMembers(channel_guid=self._resolve_object_guid(object_guid, peer=peer), start_id=start_id, search_text=search_text))

    async def ban_channel_member(self: "Client", object_guid: Any, member_guid: Any) -> BanChannelMemberResult:
        return await self.invoke(BanChannelMember(channel_guid=self._resolve_object_guid(object_guid), member_guid=self._resolve_object_guid(member_guid), action="Set"))

    async def unban_channel_member(self: "Client", object_guid: Any, member_guid: Any) -> BanChannelMemberResult:
        return await self.invoke(BanChannelMember(channel_guid=self._resolve_object_guid(object_guid), member_guid=self._resolve_object_guid(member_guid), action="Unset"))

    async def set_channel_admin(self: "Client", object_guid: Any = None, member_guid: Any = None, access_list: Sequence[Any] = (), *, peer: Any = None) -> SetGroupAdminResult:
        return await self.invoke(SetChannelAdmin(channel_guid=self._resolve_object_guid(object_guid, peer=peer), member_guid=self._resolve_object_guid(member_guid), action="SetAdmin", access_list=self._plain_list(access_list)))

    update_channel_admin_access = set_channel_admin

    async def unset_channel_admin(self: "Client", object_guid: Any = None, member_guid: Any = None, *, peer: Any = None) -> SetGroupAdminResult:
        return await self.invoke(SetChannelAdmin(channel_guid=self._resolve_object_guid(object_guid, peer=peer), member_guid=self._resolve_object_guid(member_guid), action="UnsetAdmin", access_list=None))

    async def get_channel_admin_access_list(self: "Client", object_guid: Any, member_guid: Any) -> AdminAccessList:
        return await self.invoke(GetChannelAdminAccessList(channel_guid=self._resolve_object_guid(object_guid), member_guid=self._resolve_object_guid(member_guid)))

    async def get_channel_link(self: "Client", object_guid: Any = None, *, peer: Any = None) -> ChannelLink:
        """The primary join link (``getChannelLink``). [HTTP]"""
        return await self.invoke(GetChannelLink(channel_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def set_channel_link(self: "Client", object_guid: Any) -> ChannelLink:
        """Regenerate the primary join link (``setChannelLink``). [HTTP]"""
        return await self.invoke(SetChannelLink(channel_guid=self._resolve_object_guid(object_guid)))

    async def update_channel_username(self: "Client", object_guid: Any, username: str) -> RawObject:
        return await self.invoke(UpdateChannelUsername(channel_guid=self._resolve_object_guid(object_guid), username=str(username).lstrip("@")))

    async def check_channel_username(self: "Client", username: str) -> UsernameCheck:
        return await self.invoke(CheckChannelUsername(username=str(username).lstrip("@")))

    async def join_channel_action(self: "Client", object_guid: Any, action: Any) -> JoinedChannel:
        """``joinChannelAction`` (``Join`` / ``Leave`` / ``Remove``). [HTTP]"""
        return await self.invoke(JoinChannelAction(channel_guid=self._resolve_object_guid(object_guid), action=str(getattr(action, "value", action))))

    async def join_channel(self: "Client", channel: Any) -> JoinedChannel:
        """Join a public channel by guid, or a private one by ``rubika.ir/joinc/<hash>`` link. [HTTP]"""
        value = str(channel)
        if "/joinc/" in value or "/join/" in value:
            return await self.invoke(JoinChannelByLink(hash_link=_hash_link(value)))
        return await self.join_channel_action(channel, "Join")

    async def join_channel_by_link(self: "Client", link: str) -> JoinedChannel:
        return await self.invoke(JoinChannelByLink(hash_link=_hash_link(link)))

    async def leave_channel(self: "Client", object_guid: Any) -> JoinedChannel:
        return await self.join_channel_action(object_guid, "Leave")

    async def get_channel_preview(self: "Client", link: str) -> ChannelPreview:
        return await self.invoke(ChannelPreviewByJoinLink(hash_link=_hash_link(link)))

    channel_preview_by_join_link = get_channel_preview

    async def remove_channel(self: "Client", object_guid: Any) -> RawObject:
        """Delete a channel you own (``removeChannel``). [HTTP]"""
        return await self.invoke(RemoveChannel(channel_guid=self._resolve_object_guid(object_guid)))


__all__ = ["Channels"]
