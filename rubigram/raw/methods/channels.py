"""Channel RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rubigram.raw.base import RawMethod
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
    SetGroupAdminResult,
    UsernameCheck,
)


@dataclass
class AddChannel(RawMethod[AddChannelResult]):
    title: str
    channel_type: str = "Private"
    description: Optional[str] = None
    member_guids: Optional[List[str]] = None
    thumbnail_file_id: Optional[str] = None
    main_file_id: Optional[str] = None

    method_name = "addChannel"
    result = AddChannelResult


@dataclass
class GetChannelInfo(RawMethod[ChannelInfo]):
    channel_guid: str

    method_name = "getChannelInfo"
    result = ChannelInfo


@dataclass
class EditChannelInfo(RawMethod[EditChannelInfoResult]):
    channel_guid: str
    updated_parameters: List[str]
    title: Optional[str] = None
    description: Optional[str] = None
    channel_type: Optional[str] = None
    sign_messages: Optional[bool] = None
    chat_reaction_setting: Optional[Dict[str, Any]] = None

    method_name = "editChannelInfo"
    result = EditChannelInfoResult


@dataclass
class AddChannelMembers(RawMethod[AddChannelMembersResult]):
    channel_guid: str
    member_guids: List[str]

    method_name = "addChannelMembers"
    result = AddChannelMembersResult


@dataclass
class GetChannelAllMembers(RawMethod[GroupMembers]):
    channel_guid: str
    start_id: Optional[str] = None
    search_text: Optional[str] = None

    method_name = "getChannelAllMembers"
    result = GroupMembers


@dataclass
class GetChannelAdminMembers(RawMethod[GroupMembers]):
    channel_guid: str
    start_id: Optional[str] = None
    search_text: Optional[str] = None

    method_name = "getChannelAdminMembers"
    result = GroupMembers


@dataclass
class GetBannedChannelMembers(RawMethod[GroupMembers]):
    channel_guid: str
    start_id: Optional[str] = None
    search_text: Optional[str] = None

    method_name = "getBannedChannelMembers"
    result = GroupMembers


@dataclass
class BanChannelMember(RawMethod[BanChannelMemberResult]):
    channel_guid: str
    member_guid: str
    action: str = "Set"

    method_name = "banChannelMember"
    result = BanChannelMemberResult


@dataclass
class SetChannelAdmin(RawMethod[SetGroupAdminResult]):
    channel_guid: str
    member_guid: str
    action: str = "SetAdmin"
    access_list: Optional[List[str]] = None

    method_name = "setChannelAdmin"
    result = SetGroupAdminResult

    def to_input(self) -> Dict[str, Any]:
        data = super().to_input()
        if not self.access_list:
            data.pop("access_list", None)
        return data


@dataclass
class GetChannelAdminAccessList(RawMethod[AdminAccessList]):
    channel_guid: str
    member_guid: str

    method_name = "getChannelAdminAccessList"
    result = AdminAccessList


@dataclass
class GetChannelLink(RawMethod[ChannelLink]):
    channel_guid: str

    method_name = "getChannelLink"
    result = ChannelLink


@dataclass
class SetChannelLink(RawMethod[ChannelLink]):
    channel_guid: str

    method_name = "setChannelLink"
    result = ChannelLink


@dataclass
class UpdateChannelUsername(RawMethod[Any]):
    channel_guid: str
    username: str

    method_name = "updateChannelUsername"


@dataclass
class CheckChannelUsername(RawMethod[UsernameCheck]):
    username: str

    method_name = "checkChannelUsername"
    result = UsernameCheck


@dataclass
class JoinChannelAction(RawMethod[JoinedChannel]):
    channel_guid: str
    action: str = "Join"

    method_name = "joinChannelAction"
    result = JoinedChannel


@dataclass
class JoinChannelByLink(RawMethod[JoinedChannel]):
    hash_link: str

    method_name = "joinChannelByLink"
    result = JoinedChannel


@dataclass
class ChannelPreviewByJoinLink(RawMethod[ChannelPreview]):
    hash_link: str

    method_name = "channelPreviewByJoinLink"
    result = ChannelPreview


@dataclass
class RemoveChannel(RawMethod[Any]):
    channel_guid: str

    method_name = "removeChannel"


__all__ = [
    "AddChannel",
    "GetChannelInfo",
    "EditChannelInfo",
    "AddChannelMembers",
    "GetChannelAllMembers",
    "GetChannelAdminMembers",
    "GetBannedChannelMembers",
    "BanChannelMember",
    "SetChannelAdmin",
    "GetChannelAdminAccessList",
    "GetChannelLink",
    "SetChannelLink",
    "UpdateChannelUsername",
    "CheckChannelUsername",
    "JoinChannelAction",
    "JoinChannelByLink",
    "ChannelPreviewByJoinLink",
    "RemoveChannel",
]
