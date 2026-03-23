from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

from rubigram.raw.base import RawMethod
from rubigram.types import (
    AddGroupResult,
    BanGroupMemberResult,
    CreatedJoinLink,
    EditGroupInfoResult,
    GroupDefaultAccess,
    GroupInfo,
    GroupLink,
    GroupMembers,
    JoinLinks,
    PendingObjectOwner,
    RawObject,
    SetGroupAdminResult,
)

if TYPE_CHECKING:
    import rubigram


@dataclass
class AddGroup(RawMethod[AddGroupResult]):
    """
    Create a new group and optionally add initial members.

    Requires authentication.
    """

    title: str
    member_guids: List[str]

    method_name = "addGroup"

    def to_input(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "member_guids": self.member_guids,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> AddGroupResult:
        return AddGroupResult._parse(client, data)


@dataclass
class AddGroupMembers(RawMethod[RawObject]):
    """
    Add members to an existing group.

    Requires authentication.
    """

    group_guid: str
    member_guids: List[str]

    method_name = "addGroupMembers"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
            "member_guids": self.member_guids,
        }


@dataclass
class BanGroupMember(RawMethod[BanGroupMemberResult]):
    """
    Ban a member from a group.

    Requires authentication.
    """

    group_guid: str
    member_guid: str
    action: str = "Set"

    method_name = "banGroupMember"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
            "member_guid": self.member_guid,
            "action": self.action,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> BanGroupMemberResult:
        return BanGroupMemberResult._parse(client, data)


@dataclass
class SetGroupAdmin(RawMethod[SetGroupAdminResult]):
    """
    Promote a member to admin or update admin access.

    Requires authentication.
    """

    group_guid: str
    member_guid: str
    access_list: List[str]
    action: str = "SetAdmin"

    method_name = "setGroupAdmin"

    def to_input(self) -> Dict[str, Any]:
        input_dict: Dict[str, Any] = {
            "group_guid": self.group_guid,
            "member_guid": self.member_guid,
            "action": self.action,
        }
        if self.access_list:
            input_dict["access_list"] = self.access_list
        return input_dict

    def parse_response(self, client: "rubigram.Client", data: Any) -> SetGroupAdminResult:
        return SetGroupAdminResult._parse(client, data)


@dataclass
class UploadNewGroupAvatar(RawMethod[RawObject]):
    """
    Set a new group avatar using a previously uploaded file.

    Requires authentication.
    """

    group_guid: str
    file_id: str
    dc_id: str
    access_hash_rec: str

    method_name = "uploadNewGroupAvatar"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
            "file_id": self.file_id,
            "dc_id": self.dc_id,
            "access_hash_rec": self.access_hash_rec,
        }


@dataclass
class GetGroupInfo(RawMethod[GroupInfo]):
    """
    Get detailed information about a group.

    Requires authentication.
    """

    group_guid: str

    method_name = "getGroupInfo"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> GroupInfo:
        return GroupInfo._parse(client, data)


@dataclass
class GetGroupAllMembers(RawMethod[GroupMembers]):
    """
    Get all current members of a group.

    Requires authentication.
    """

    group_guid: str

    method_name = "getGroupAllMembers"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> GroupMembers:
        return GroupMembers._parse(client, data)


@dataclass
class GetGroupDefaultAccess(RawMethod[GroupDefaultAccess]):
    """
    Get the default access list for group members.

    Requires authentication.
    """

    group_guid: str

    method_name = "getGroupDefaultAccess"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> GroupDefaultAccess:
        return GroupDefaultAccess._parse(client, data)


@dataclass
class SetGroupDefaultAccess(RawMethod[RawObject]):
    """
    Set the default access list for regular group members.

    Requires authentication.
    """

    group_guid: str
    access_list: List[str]

    method_name = "setGroupDefaultAccess"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
            "access_list": self.access_list,
        }


@dataclass
class GetPendingObjectOwner(RawMethod[PendingObjectOwner]):
    """
    Check whether an object has a pending owner transfer awaiting confirmation.

    Requires authentication.
    """

    object_guid: str

    method_name = "getPendingObjectOwner"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> PendingObjectOwner:
        return PendingObjectOwner._parse(client, data)


@dataclass
class GetGroupLink(RawMethod[GroupLink]):
    """
    Get the current join link for a group.

    Requires authentication.
    """

    group_guid: str

    method_name = "getGroupLink"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> GroupLink:
        return GroupLink._parse(client, data)


@dataclass
class GetJoinLinks(RawMethod[JoinLinks]):
    """
    Get the list of generated join links for an object.

    Requires authentication.
    """

    object_guid: str

    method_name = "getJoinLinks"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> JoinLinks:
        return JoinLinks._parse(client, data)


@dataclass
class RequestChangeObjectOwner(RawMethod[RawObject]):
    """
    Request transferring ownership of an object to another user.

    Requires authentication.
    """

    object_guid: str
    new_owner_user_guid: str

    method_name = "requestChangeObjectOwner"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
            "new_owner_user_guid": self.new_owner_user_guid,
        }


@dataclass
class RemoveGroup(RawMethod[RawObject]):
    """
    Request removing a group.

    Requires authentication.
    """

    group_guid: str

    method_name = "removeGroup"

    def to_input(self) -> Dict[str, Any]:
        return {
            "group_guid": self.group_guid,
        }


@dataclass
class CreateJoinLink(RawMethod[CreatedJoinLink]):
    """
    Create a new join link for an object.

    Requires authentication.
    """

    object_guid: str
    title: str
    request_needed: bool = False
    expire_time: int = 0
    usage_limit: int = 0

    method_name = "createJoinLink"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
            "title": self.title,
            "request_needed": self.request_needed,
            "expire_time": self.expire_time,
            "usage_limit": self.usage_limit,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> CreatedJoinLink:
        return CreatedJoinLink._parse(client, data)


@dataclass
class EditGroupInfo(RawMethod[EditGroupInfoResult]):
    """
    Edit supported group info flags.

    Requires authentication.
    """

    group_guid: str
    updated_parameters: List[str]
    event_messages: bool | None = None
    chat_history_for_new_members: str | None = None
    chat_reaction_setting: Dict[str, Any] | None = None
    slow_mode: int | None = None

    method_name = "editGroupInfo"

    def to_input(self) -> Dict[str, Any]:
        input_dict: Dict[str, Any] = {
            "group_guid": self.group_guid,
            "updated_parameters": self.updated_parameters,
        }
        if self.event_messages is not None:
            input_dict["event_messages"] = self.event_messages
        if self.chat_history_for_new_members is not None:
            input_dict["chat_history_for_new_members"] = self.chat_history_for_new_members
        if self.chat_reaction_setting is not None:
            input_dict["chat_reaction_setting"] = self.chat_reaction_setting
        if self.slow_mode is not None:
            input_dict["slow_mode"] = self.slow_mode
        return input_dict

    def parse_response(self, client: "rubigram.Client", data: Any) -> EditGroupInfoResult:
        return EditGroupInfoResult._parse(client, data)
