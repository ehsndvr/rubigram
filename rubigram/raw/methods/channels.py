from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

from rubigram.raw.base import RawMethod
from rubigram.types import AddChannelMembersResult, AddChannelResult, ChannelInfo, EditChannelInfoResult, Empty, GroupMembers, SetGroupAdminResult

if TYPE_CHECKING:
    import rubigram


@dataclass
class AddChannel(RawMethod[AddChannelResult]):
    """
    Create a new channel.

    Requires authentication.
    """

    title: str
    description: str
    channel_type: str
    member_guids: List[str]
    thumbnail_file_id: str
    main_file_id: str

    method_name = "addChannel"

    def to_input(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "channel_type": self.channel_type,
            "member_guids": self.member_guids,
            "thumbnail_file_id": self.thumbnail_file_id,
            "main_file_id": self.main_file_id,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> AddChannelResult:
        return AddChannelResult._parse(client, data)


@dataclass
class AddChannelMembers(RawMethod[AddChannelMembersResult]):
    """
    Add members to an existing channel.

    Requires authentication.
    """

    channel_guid: str
    member_guids: List[str]

    method_name = "addChannelMembers"

    def to_input(self) -> Dict[str, Any]:
        return {
            "channel_guid": self.channel_guid,
            "member_guids": self.member_guids,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> AddChannelMembersResult:
        return AddChannelMembersResult._parse(client, data)


@dataclass
class GetChannelLink(RawMethod[Empty]):
    """
    Get the active join/link state for a channel.

    Requires authentication.
    """

    channel_guid: str

    method_name = "getChannelLink"

    def to_input(self) -> Dict[str, Any]:
        return {
            "channel_guid": self.channel_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> Empty:
        return Empty._parse(client, data or {})


@dataclass
class GetChannelInfo(RawMethod[ChannelInfo]):
    """
    Get detailed information about a channel.

    Requires authentication.
    """

    channel_guid: str

    method_name = "getChannelInfo"

    def to_input(self) -> Dict[str, Any]:
        return {
            "channel_guid": self.channel_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> ChannelInfo:
        return ChannelInfo._parse(client, data)


@dataclass
class GetChannelAllMembers(RawMethod[GroupMembers]):
    """
    Get all current members of a channel.

    Requires authentication.
    """

    channel_guid: str

    method_name = "getChannelAllMembers"

    def to_input(self) -> Dict[str, Any]:
        return {
            "channel_guid": self.channel_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> GroupMembers:
        return GroupMembers._parse(client, data)


@dataclass
class EditChannelInfo(RawMethod[EditChannelInfoResult]):
    """
    Edit mutable channel info fields.

    Requires authentication.
    """

    channel_guid: str
    updated_parameters: List[str]
    title: str | None = None
    description: str | None = None

    method_name = "editChannelInfo"

    def to_input(self) -> Dict[str, Any]:
        input_dict: Dict[str, Any] = {
            "channel_guid": self.channel_guid,
            "updated_parameters": self.updated_parameters,
        }
        if self.title is not None:
            input_dict["title"] = self.title
        if self.description is not None:
            input_dict["description"] = self.description
        return input_dict

    def parse_response(self, client: "rubigram.Client", data: Any) -> EditChannelInfoResult:
        return EditChannelInfoResult._parse(client, data)


@dataclass
class GetChannelAdminMembers(RawMethod[GroupMembers]):
    """
    Get current admin members of a channel.

    Requires authentication.
    """

    channel_guid: str

    method_name = "getChannelAdminMembers"

    def to_input(self) -> Dict[str, Any]:
        return {
            "channel_guid": self.channel_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> GroupMembers:
        return GroupMembers._parse(client, data)


@dataclass
class SetChannelAdmin(RawMethod[SetGroupAdminResult]):
    """
    Promote a member to channel admin or update channel admin access.

    Requires authentication.
    """

    channel_guid: str
    member_guid: str
    access_list: List[str]
    action: str = "SetAdmin"

    method_name = "setChannelAdmin"

    def to_input(self) -> Dict[str, Any]:
        input_dict: Dict[str, Any] = {
            "channel_guid": self.channel_guid,
            "member_guid": self.member_guid,
            "action": self.action,
        }
        if self.access_list:
            input_dict["access_list"] = self.access_list
        return input_dict

    def parse_response(self, client: "rubigram.Client", data: Any) -> SetGroupAdminResult:
        return SetGroupAdminResult._parse(client, data)


@dataclass
class GetBannedChannelMembers(RawMethod[GroupMembers]):
    """
    Get current banned members of a channel.

    Requires authentication.
    """

    channel_guid: str

    method_name = "getBannedChannelMembers"

    def to_input(self) -> Dict[str, Any]:
        return {
            "channel_guid": self.channel_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> GroupMembers:
        return GroupMembers._parse(client, data)
