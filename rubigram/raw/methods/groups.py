"""Group RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import (
    AddGroupMembersResult,
    AddGroupResult,
    AdminAccessList,
    BanGroupMemberResult,
    CreatedJoinLink,
    EditGroupInfoResult,
    Empty,
    GroupDefaultAccess,
    GroupInfo,
    GroupLink,
    GroupMembers,
    GroupOnlineCount,
    GroupPreview,
    JoinedGroup,
    JoinLinks,
    JoinRequests,
    MentionList,
    OwnerRequestResult,
    PendingObjectOwner,
    SetGroupAdminResult,
)


@dataclass
class AddGroup(RawMethod[AddGroupResult]):
    title: str
    member_guids: List[str]

    method_name = "addGroup"
    result = AddGroupResult


@dataclass
class GetGroupInfo(RawMethod[GroupInfo]):
    group_guid: str

    method_name = "getGroupInfo"
    result = GroupInfo


@dataclass
class EditGroupInfo(RawMethod[EditGroupInfoResult]):
    group_guid: str
    updated_parameters: List[str]
    title: Optional[str] = None
    description: Optional[str] = None
    slow_mode: Optional[int] = None
    chat_history_for_new_members: Optional[str] = None
    event_messages: Optional[bool] = None
    chat_reaction_setting: Optional[Dict[str, Any]] = None
    sign_messages: Optional[bool] = None

    method_name = "editGroupInfo"
    result = EditGroupInfoResult


@dataclass
class AddGroupMembers(RawMethod[AddGroupMembersResult]):
    group_guid: str
    member_guids: List[str]

    method_name = "addGroupMembers"
    result = AddGroupMembersResult


@dataclass
class GetGroupAllMembers(RawMethod[GroupMembers]):
    group_guid: str
    start_id: Optional[str] = None
    search_text: Optional[str] = None

    method_name = "getGroupAllMembers"
    result = GroupMembers


@dataclass
class GetGroupAdminMembers(RawMethod[GroupMembers]):
    group_guid: str
    start_id: Optional[str] = None
    search_text: Optional[str] = None

    method_name = "getGroupAdminMembers"
    result = GroupMembers


@dataclass
class GetBannedGroupMembers(RawMethod[GroupMembers]):
    group_guid: str
    start_id: Optional[str] = None
    search_text: Optional[str] = None

    method_name = "getBannedGroupMembers"
    result = GroupMembers


@dataclass
class BanGroupMember(RawMethod[BanGroupMemberResult]):
    group_guid: str
    member_guid: str
    action: str = "Set"

    method_name = "banGroupMember"
    result = BanGroupMemberResult


@dataclass
class SetGroupAdmin(RawMethod[SetGroupAdminResult]):
    group_guid: str
    member_guid: str
    action: str = "SetAdmin"
    access_list: Optional[List[str]] = None

    method_name = "setGroupAdmin"
    result = SetGroupAdminResult

    def to_input(self) -> Dict[str, Any]:
        data = super().to_input()
        if not self.access_list:
            data.pop("access_list", None)
        return data


@dataclass
class GetGroupAdminAccessList(RawMethod[AdminAccessList]):
    group_guid: str
    member_guid: str

    method_name = "getGroupAdminAccessList"
    result = AdminAccessList


@dataclass
class GetGroupDefaultAccess(RawMethod[GroupDefaultAccess]):
    group_guid: str

    method_name = "getGroupDefaultAccess"
    result = GroupDefaultAccess


@dataclass
class SetGroupDefaultAccess(RawMethod[Empty]):
    group_guid: str
    access_list: List[str]

    method_name = "setGroupDefaultAccess"
    result = Empty


@dataclass
class GetGroupLink(RawMethod[GroupLink]):
    group_guid: str

    method_name = "getGroupLink"
    result = GroupLink


@dataclass
class SetGroupLink(RawMethod[GroupLink]):
    group_guid: str

    method_name = "setGroupLink"
    result = GroupLink


@dataclass
class GetGroupOnlineCount(RawMethod[GroupOnlineCount]):
    group_guid: str

    method_name = "getGroupOnlineCount"
    result = GroupOnlineCount


@dataclass
class GetGroupMentionList(RawMethod[MentionList]):
    group_guid: str
    search_mention: Optional[str] = None

    method_name = "getGroupMentionList"
    result = MentionList


@dataclass
class LeaveGroup(RawMethod[Any]):
    group_guid: str

    method_name = "leaveGroup"


@dataclass
class JoinGroup(RawMethod[JoinedGroup]):
    hash_link: str

    method_name = "joinGroup"
    result = JoinedGroup


@dataclass
class GroupPreviewByJoinLink(RawMethod[GroupPreview]):
    hash_link: str

    method_name = "groupPreviewByJoinLink"
    result = GroupPreview


@dataclass
class RemoveGroup(RawMethod[Any]):
    group_guid: str

    method_name = "removeGroup"


@dataclass
class RequestChangeObjectOwner(RawMethod[OwnerRequestResult]):
    object_guid: str
    new_owner_user_guid: str

    method_name = "requestChangeObjectOwner"
    result = OwnerRequestResult


@dataclass
class CancelChangeObjectOwner(RawMethod[OwnerRequestResult]):
    object_guid: str

    method_name = "cancelChangeObjectOwner"
    result = OwnerRequestResult


@dataclass
class ReplyRequestObjectOwner(RawMethod[OwnerRequestResult]):
    object_guid: str
    action: str

    method_name = "replyRequestObjectOwner"
    result = OwnerRequestResult


@dataclass
class GetPendingObjectOwner(RawMethod[PendingObjectOwner]):
    object_guid: str

    method_name = "getPendingObjectOwner"
    result = PendingObjectOwner


# -- join links and requests (shared by groups and channels) -----------------


@dataclass
class GetJoinLinks(RawMethod[JoinLinks]):
    object_guid: str
    creator_guid: Optional[str] = None

    method_name = "getJoinLinks"
    result = JoinLinks


@dataclass
class CreateJoinLink(RawMethod[CreatedJoinLink]):
    object_guid: str
    title: str = ""
    request_needed: bool = False
    expire_time: int = 0
    usage_limit: int = 0

    method_name = "createJoinLink"
    result = CreatedJoinLink


@dataclass
class EditJoinLink(RawMethod[CreatedJoinLink]):
    object_guid: str
    join_link: str
    updated_parameters: List[str]
    title: Optional[str] = None
    request_needed: Optional[bool] = None
    expire_time: Optional[int] = None
    usage_limit: Optional[int] = None

    method_name = "editJoinLink"
    result = CreatedJoinLink


@dataclass
class RevokeJoinLink(RawMethod[Any]):
    object_guid: str
    join_link: str

    method_name = "revokeJoinLink"


@dataclass
class DeleteRevokedJoinLink(RawMethod[Any]):
    object_guid: str
    join_link: Optional[str] = None

    method_name = "deleteRevokedJoinLink"


@dataclass
class GetJoinRequests(RawMethod[JoinRequests]):
    object_guid: str
    start_id: Optional[str] = None

    method_name = "getJoinRequests"
    result = JoinRequests


@dataclass
class ActionOnJoinRequest(RawMethod[Any]):
    object_guid: str
    user_guid: str
    action: str

    method_name = "actionOnJoinRequest"


@dataclass
class GetJoinLinkUserJoined(RawMethod[Any]):
    object_guid: str
    join_link: str
    start_id: Optional[str] = None

    method_name = "getJoinLinkUserJoined"


__all__ = [
    "ActionOnJoinRequest",
    "AddGroup",
    "AddGroupMembers",
    "BanGroupMember",
    "CancelChangeObjectOwner",
    "CreateJoinLink",
    "DeleteRevokedJoinLink",
    "EditGroupInfo",
    "EditJoinLink",
    "GetBannedGroupMembers",
    "GetGroupAdminAccessList",
    "GetGroupAdminMembers",
    "GetGroupAllMembers",
    "GetGroupDefaultAccess",
    "GetGroupInfo",
    "GetGroupLink",
    "GetGroupMentionList",
    "GetGroupOnlineCount",
    "GetJoinLinkUserJoined",
    "GetJoinLinks",
    "GetJoinRequests",
    "GetPendingObjectOwner",
    "GroupPreviewByJoinLink",
    "JoinGroup",
    "LeaveGroup",
    "RemoveGroup",
    "ReplyRequestObjectOwner",
    "RequestChangeObjectOwner",
    "RevokeJoinLink",
    "SetGroupAdmin",
    "SetGroupDefaultAccess",
    "SetGroupLink",
]
