from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

from rubigram.raw.base import RawMethod
from rubigram.types import AddChannelResult, ChannelInfo, Empty, GroupMembers

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
