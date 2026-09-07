"""Groups: info, members, admins, access, links, join/leave, ownership."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence

from rubigram.raw.functions import build_updated_parameters
from rubigram.raw.methods import (
    AddGroup,
    AddGroupMembers,
    BanGroupMember,
    CancelChangeObjectOwner,
    EditGroupInfo,
    GetBannedGroupMembers,
    GetGroupAdminAccessList,
    GetGroupAdminMembers,
    GetGroupAllMembers,
    GetGroupDefaultAccess,
    GetGroupInfo,
    GetGroupLink,
    GetGroupMentionList,
    GetGroupOnlineCount,
    GetPendingObjectOwner,
    GroupPreviewByJoinLink,
    JoinGroup,
    LeaveGroup,
    RemoveGroup,
    ReplyRequestObjectOwner,
    RequestChangeObjectOwner,
    SetGroupAdmin,
    SetGroupDefaultAccess,
    SetGroupLink,
)
from rubigram.types import (
    AddGroupMembersResult,
    AddGroupResult,
    AdminAccessList,
    BanGroupMemberResult,
    EditGroupInfoResult,
    Empty,
    GroupDefaultAccess,
    GroupInfo,
    GroupLink,
    GroupMembers,
    GroupOnlineCount,
    GroupPreview,
    JoinedGroup,
    MentionList,
    OwnerRequestResult,
    PendingObjectOwner,
    RawObject,
    SetGroupAdminResult,
)

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client

_EDITABLE = ("title", "description", "slow_mode", "chat_history_for_new_members", "event_messages", "chat_reaction_setting", "sign_messages")


def _hash_link(value: str) -> str:
    """Accept a full ``rubika.ir/joing/<hash>`` link or the bare hash."""
    text = str(value).strip()
    for marker in ("/joing/", "/joinc/", "/join/"):
        if marker in text:
            return text.split(marker, 1)[1].split("?")[0].strip("/")
    return text


class Groups:
    async def add_group(self: "Client", title: str, member_guids: Sequence[Any] | None = None) -> AddGroupResult:
        """Create a group (``addGroup``). [HTTP]"""
        return await self.invoke(AddGroup(title=title, member_guids=self._resolve_guids(member_guids)))

    create_group = add_group

    async def get_group_info(self: "Client", object_guid: Any = None, *, peer: Any = None) -> GroupInfo:
        """``getGroupInfo``. [HTTP]"""
        return await self.invoke(GetGroupInfo(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def edit_group_info(
        self: "Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        slow_mode: Optional[int] = None,
        chat_history_for_new_members: Optional[Any] = None,
        event_messages: Optional[bool] = None,
        chat_reaction_setting: Optional[Dict[str, Any]] = None,
        sign_messages: Optional[bool] = None,
    ) -> EditGroupInfoResult:
        """Change group settings (``editGroupInfo``); only the given fields are sent. [HTTP]"""
        values, names = build_updated_parameters(
            {
                "title": title,
                "description": description,
                "slow_mode": slow_mode,
                "chat_history_for_new_members": chat_history_for_new_members,
                "event_messages": event_messages,
                "chat_reaction_setting": chat_reaction_setting,
                "sign_messages": sign_messages,
            },
            allowed=_EDITABLE,
        )
        if not names:
            raise ValueError("At least one supported group field must be provided")
        return await self.invoke(EditGroupInfo(group_guid=self._resolve_object_guid(object_guid, peer=peer), updated_parameters=names, **values))

    async def set_group_title(self: "Client", object_guid: Any, title: str, *, description: Optional[str] = None) -> EditGroupInfoResult:
        return await self.edit_group_info(object_guid, title=title, description=description)

    async def set_group_event_messages(self: "Client", object_guid: Any = None, enabled: bool = True, *, peer: Any = None) -> EditGroupInfoResult:
        return await self.edit_group_info(object_guid, peer=peer, event_messages=enabled)

    async def set_group_history_for_new_members(self: "Client", object_guid: Any = None, value: Any = "Visible", *, peer: Any = None) -> EditGroupInfoResult:
        return await self.edit_group_info(object_guid, peer=peer, chat_history_for_new_members=value)

    async def set_group_slow_mode(self: "Client", object_guid: Any = None, seconds: int = 0, *, peer: Any = None) -> EditGroupInfoResult:
        return await self.edit_group_info(object_guid, peer=peer, slow_mode=seconds)

    async def set_group_reaction_setting(self: "Client", object_guid: Any = None, *, peer: Any = None, reaction_type: Any = "All", selected_reactions: Sequence[Any] | None = None) -> EditGroupInfoResult:
        setting: Dict[str, Any] = {"reaction_type": str(getattr(reaction_type, "value", reaction_type))}
        if selected_reactions is not None:
            setting["selected_reactions"] = [str(item) for item in selected_reactions]
        return await self.edit_group_info(object_guid, peer=peer, chat_reaction_setting=setting)

    async def set_group_reactions_all(self: "Client", object_guid: Any = None, *, peer: Any = None) -> EditGroupInfoResult:
        return await self.set_group_reaction_setting(object_guid, peer=peer, reaction_type="All")

    async def set_group_reactions_disabled(self: "Client", object_guid: Any = None, *, peer: Any = None) -> EditGroupInfoResult:
        return await self.set_group_reaction_setting(object_guid, peer=peer, reaction_type="Disabled")

    async def set_group_reactions_selected(self: "Client", object_guid: Any = None, selected_reactions: Sequence[Any] | None = None, *, peer: Any = None) -> EditGroupInfoResult:
        return await self.set_group_reaction_setting(object_guid, peer=peer, reaction_type="Selected", selected_reactions=selected_reactions)

    async def add_group_members(self: "Client", object_guid: Any = None, member_guids: Sequence[Any] | None = None, *, peer: Any = None) -> AddGroupMembersResult:
        """``addGroupMembers``. [HTTP]"""
        return await self.invoke(AddGroupMembers(group_guid=self._resolve_object_guid(object_guid, peer=peer), member_guids=self._resolve_guids(member_guids)))

    async def get_group_all_members(self: "Client", object_guid: Any = None, *, peer: Any = None, start_id: Optional[str] = None, search_text: Optional[str] = None) -> GroupMembers:
        """One page of members (``getGroupAllMembers``); ``next_start_id`` continues. [HTTP]"""
        return await self.invoke(GetGroupAllMembers(group_guid=self._resolve_object_guid(object_guid, peer=peer), start_id=start_id, search_text=search_text))

    async def get_group_admin_members(self: "Client", object_guid: Any = None, *, peer: Any = None, start_id: Optional[str] = None, search_text: Optional[str] = None) -> GroupMembers:
        return await self.invoke(GetGroupAdminMembers(group_guid=self._resolve_object_guid(object_guid, peer=peer), start_id=start_id, search_text=search_text))

    async def get_banned_group_members(self: "Client", object_guid: Any = None, *, peer: Any = None, start_id: Optional[str] = None, search_text: Optional[str] = None) -> GroupMembers:
        return await self.invoke(GetBannedGroupMembers(group_guid=self._resolve_object_guid(object_guid, peer=peer), start_id=start_id, search_text=search_text))

    async def ban_group_member(self: "Client", object_guid: Any = None, member_guid: Any = None, *, peer: Any = None) -> BanGroupMemberResult:
        """``banGroupMember`` / ``Set``. [HTTP]"""
        return await self.invoke(BanGroupMember(group_guid=self._resolve_object_guid(object_guid, peer=peer), member_guid=self._resolve_object_guid(member_guid), action="Set"))

    async def unban_group_member(self: "Client", object_guid: Any = None, member_guid: Any = None, *, peer: Any = None) -> BanGroupMemberResult:
        return await self.invoke(BanGroupMember(group_guid=self._resolve_object_guid(object_guid, peer=peer), member_guid=self._resolve_object_guid(member_guid), action="Unset"))

    async def set_group_admin(self: "Client", object_guid: Any = None, member_guid: Any = None, access_list: Sequence[Any] = (), *, peer: Any = None) -> SetGroupAdminResult:
        """Promote a member (``setGroupAdmin`` / ``SetAdmin``) with a :class:`~rubigram.enums.GroupAdminAccess` list. [HTTP]"""
        return await self.invoke(SetGroupAdmin(group_guid=self._resolve_object_guid(object_guid, peer=peer), member_guid=self._resolve_object_guid(member_guid), action="SetAdmin", access_list=self._plain_list(access_list)))

    update_group_admin_access = set_group_admin

    async def unset_group_admin(self: "Client", object_guid: Any = None, member_guid: Any = None, *, peer: Any = None) -> SetGroupAdminResult:
        return await self.invoke(SetGroupAdmin(group_guid=self._resolve_object_guid(object_guid, peer=peer), member_guid=self._resolve_object_guid(member_guid), action="UnsetAdmin", access_list=None))

    async def get_group_admin_access_list(self: "Client", object_guid: Any, member_guid: Any) -> AdminAccessList:
        return await self.invoke(GetGroupAdminAccessList(group_guid=self._resolve_object_guid(object_guid), member_guid=self._resolve_object_guid(member_guid)))

    async def get_group_default_access(self: "Client", object_guid: Any = None, *, peer: Any = None) -> GroupDefaultAccess:
        return await self.invoke(GetGroupDefaultAccess(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def set_group_default_access(self: "Client", object_guid: Any = None, access_list: Sequence[Any] = (), *, peer: Any = None) -> Empty:
        return await self.invoke(SetGroupDefaultAccess(group_guid=self._resolve_object_guid(object_guid, peer=peer), access_list=self._plain_list(access_list)))

    async def get_group_link(self: "Client", object_guid: Any = None, *, peer: Any = None) -> GroupLink:
        return await self.invoke(GetGroupLink(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def set_group_link(self: "Client", object_guid: Any) -> GroupLink:
        """Regenerate the primary join link (``setGroupLink``). [HTTP]"""
        return await self.invoke(SetGroupLink(group_guid=self._resolve_object_guid(object_guid)))

    async def get_group_online_count(self: "Client", object_guid: Any) -> GroupOnlineCount:
        return await self.invoke(GetGroupOnlineCount(group_guid=self._resolve_object_guid(object_guid)))

    async def get_group_mention_list(self: "Client", object_guid: Any, search_mention: Optional[str] = None) -> MentionList:
        return await self.invoke(GetGroupMentionList(group_guid=self._resolve_object_guid(object_guid), search_mention=search_mention))

    async def leave_group(self: "Client", object_guid: Any) -> RawObject:
        """``leaveGroup``. [HTTP]"""
        return await self.invoke(LeaveGroup(group_guid=self._resolve_object_guid(object_guid)))

    async def join_group(self: "Client", link: str) -> JoinedGroup:
        """Join by ``rubika.ir/joing/<hash>`` link or bare hash (``joinGroup``). [HTTP]"""
        return await self.invoke(JoinGroup(hash_link=_hash_link(link)))

    async def get_group_preview(self: "Client", link: str) -> GroupPreview:
        """Preview a group before joining (``groupPreviewByJoinLink``). [HTTP]"""
        return await self.invoke(GroupPreviewByJoinLink(hash_link=_hash_link(link)))

    group_preview_by_join_link = get_group_preview

    async def remove_group(self: "Client", object_guid: Any = None, *, peer: Any = None) -> RawObject:
        """Delete a group you own (``removeGroup``). [HTTP]"""
        return await self.invoke(RemoveGroup(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def request_change_object_owner(self: "Client", object_guid: Any = None, new_owner_user_guid: Any = None, *, peer: Any = None) -> OwnerRequestResult:
        return await self.invoke(RequestChangeObjectOwner(object_guid=self._resolve_object_guid(object_guid, peer=peer), new_owner_user_guid=self._resolve_user_guid(new_owner_user_guid)))

    async def cancel_change_object_owner(self: "Client", object_guid: Any) -> OwnerRequestResult:
        return await self.invoke(CancelChangeObjectOwner(object_guid=self._resolve_object_guid(object_guid)))

    async def reply_request_object_owner(self: "Client", object_guid: Any, action: Any) -> OwnerRequestResult:
        return await self.invoke(ReplyRequestObjectOwner(object_guid=self._resolve_object_guid(object_guid), action=str(getattr(action, "value", action))))

    async def get_pending_object_owner(self: "Client", object_guid: Any = None, *, peer: Any = None) -> PendingObjectOwner:
        return await self.invoke(GetPendingObjectOwner(object_guid=self._resolve_object_guid(object_guid, peer=peer)))


__all__ = ["Groups"]
