from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Callable, Sequence

import rubigram
from rubigram.raw.methods import (
    AddGroup,
    AddGroupMembers,
    BanGroupMember,
    CreateJoinLink,
    EditGroupInfo,
    SetGroupAdmin,
    SetGroupDefaultAccess,
    GetGroupAllMembers,
    GetGroupDefaultAccess,
    GetGroupInfo,
    GetGroupLink,
    GetJoinLinks,
    GetPendingObjectOwner,
    RequestChangeObjectOwner,
    RemoveGroup,
    UploadNewGroupAvatar,
)
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


class Groups:
    async def remove_group(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> RawObject:
        return await self.invoke(
            RemoveGroup(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
            )
        )

    async def request_change_object_owner(
        self: "rubigram.Client",
        object_guid: Any = None,
        new_owner_user_guid: Any = None,
        *,
        peer: Any = None,
    ) -> RawObject:
        return await self.invoke(
            RequestChangeObjectOwner(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                new_owner_user_guid=self._resolve_user_guid(new_owner_user_guid),
            )
        )

    @staticmethod
    def _normalize_group_access_list(access_list: Sequence[Any]) -> list[str]:
        normalized: list[str] = []
        for item in access_list:
            if isinstance(item, Enum):
                normalized.append(str(item.value))
            else:
                normalized.append(str(item))
        return normalized

    async def set_group_admin(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        access_list: Sequence[Any] = (),
        *,
        peer: Any = None,
    ) -> SetGroupAdminResult:
        return await self.invoke(
            SetGroupAdmin(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guid=self._resolve_object_guid(member_guid),
                action="SetAdmin",
                access_list=self._normalize_group_access_list(access_list),
            )
        )

    async def update_group_admin_access(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        access_list: Sequence[Any] = (),
        *,
        peer: Any = None,
    ) -> SetGroupAdminResult:
        return await self.set_group_admin(object_guid, member_guid, access_list, peer=peer)

    async def unset_group_admin(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        *,
        peer: Any = None,
    ) -> SetGroupAdminResult:
        return await self.invoke(
            SetGroupAdmin(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guid=self._resolve_object_guid(member_guid),
                action="UnsetAdmin",
                access_list=[],
            )
        )

    async def ban_group_member(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        *,
        peer: Any = None,
    ) -> BanGroupMemberResult:
        return await self.invoke(
            BanGroupMember(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guid=self._resolve_object_guid(member_guid),
                action="Set",
            )
        )

    async def unban_group_member(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        *,
        peer: Any = None,
    ) -> BanGroupMemberResult:
        return await self.invoke(
            BanGroupMember(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guid=self._resolve_object_guid(member_guid),
                action="Unset",
            )
        )

    async def edit_group_info(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
        event_messages: bool | None = None,
        chat_history_for_new_members: str | None = None,
        chat_reaction_setting: dict[str, Any] | None = None,
        slow_mode: int | None = None,
    ) -> EditGroupInfoResult:
        updated_parameters: list[str] = []
        if event_messages is not None:
            updated_parameters.append("event_messages")
        if chat_history_for_new_members is not None:
            updated_parameters.append("chat_history_for_new_members")
        if chat_reaction_setting is not None:
            updated_parameters.append("chat_reaction_setting")
        if slow_mode is not None:
            updated_parameters.append("slow_mode")
        if not updated_parameters:
            raise ValueError("At least one supported group field must be provided")
        return await self.invoke(
            EditGroupInfo(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                updated_parameters=updated_parameters,
                event_messages=event_messages,
                chat_history_for_new_members=chat_history_for_new_members,
                chat_reaction_setting=chat_reaction_setting,
                slow_mode=slow_mode,
            )
        )

    async def set_group_event_messages(
        self: "rubigram.Client",
        object_guid: Any = None,
        enabled: bool = True,
        *,
        peer: Any = None,
    ) -> EditGroupInfoResult:
        return await self.edit_group_info(object_guid, peer=peer, event_messages=enabled)

    async def set_group_history_for_new_members(
        self: "rubigram.Client",
        object_guid: Any = None,
        value: str = "Visible",
        *,
        peer: Any = None,
    ) -> EditGroupInfoResult:
        return await self.edit_group_info(object_guid, peer=peer, chat_history_for_new_members=value)

    async def set_group_slow_mode(
        self: "rubigram.Client",
        object_guid: Any = None,
        seconds: int = 0,
        *,
        peer: Any = None,
    ) -> EditGroupInfoResult:
        return await self.edit_group_info(object_guid, peer=peer, slow_mode=seconds)

    async def set_group_reaction_setting(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
        reaction_type: str = "All",
        selected_reactions: Sequence[str] | None = None,
    ) -> EditGroupInfoResult:
        setting: dict[str, Any] = {"reaction_type": reaction_type}
        if selected_reactions is not None:
            setting["selected_reactions"] = [str(item) for item in selected_reactions]
        return await self.edit_group_info(object_guid, peer=peer, chat_reaction_setting=setting)

    async def set_group_reactions_all(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> EditGroupInfoResult:
        return await self.set_group_reaction_setting(object_guid, peer=peer, reaction_type="All")

    async def set_group_reactions_disabled(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> EditGroupInfoResult:
        return await self.set_group_reaction_setting(object_guid, peer=peer, reaction_type="Disabled")

    async def set_group_reactions_selected(
        self: "rubigram.Client",
        object_guid: Any = None,
        selected_reactions: Sequence[str] | None = None,
        *,
        peer: Any = None,
    ) -> EditGroupInfoResult:
        return await self.set_group_reaction_setting(
            object_guid,
            peer=peer,
            reaction_type="Selected",
            selected_reactions=selected_reactions,
        )

    async def get_group_info(self: "rubigram.Client", object_guid: Any = None, *, peer: Any = None) -> GroupInfo:
        return await self.invoke(GetGroupInfo(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_group_all_members(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> GroupMembers:
        return await self.invoke(GetGroupAllMembers(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_group_default_access(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> GroupDefaultAccess:
        return await self.invoke(GetGroupDefaultAccess(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def set_group_default_access(
        self: "rubigram.Client",
        object_guid: Any = None,
        access_list: Sequence[Any] = (),
        *,
        peer: Any = None,
    ) -> RawObject:
        return await self.invoke(
            SetGroupDefaultAccess(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                access_list=self._normalize_group_access_list(access_list),
            )
        )

    async def get_pending_object_owner(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> PendingObjectOwner:
        return await self.invoke(GetPendingObjectOwner(object_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_group_link(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> GroupLink:
        return await self.invoke(GetGroupLink(group_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_join_links(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> JoinLinks:
        return await self.invoke(GetJoinLinks(object_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def create_join_link(
        self: "rubigram.Client",
        object_guid: Any = None,
        title: str = "",
        *,
        peer: Any = None,
        request_needed: bool = False,
        expire_time: int = 0,
        usage_limit: int = 0,
    ) -> CreatedJoinLink:
        return await self.invoke(
            CreateJoinLink(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                title=title,
                request_needed=request_needed,
                expire_time=expire_time,
                usage_limit=usage_limit,
            )
        )

    async def add_group(
        self: "rubigram.Client",
        title: str,
        member_guids: Sequence[Any] | None = None,
    ) -> AddGroupResult:
        resolved_members = [self._resolve_object_guid(member) for member in member_guids or ()]
        return await self.invoke(AddGroup(title=title, member_guids=resolved_members))

    async def create_group(
        self: "rubigram.Client",
        title: str,
        member_guids: Sequence[Any] | None = None,
    ) -> AddGroupResult:
        return await self.add_group(title=title, member_guids=member_guids)

    async def add_group_members(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guids: Sequence[Any] | None = None,
        *,
        peer: Any = None,
    ) -> RawObject:
        resolved_members = [self._resolve_object_guid(member) for member in member_guids or ()]
        return await self.invoke(
            AddGroupMembers(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guids=resolved_members,
            )
        )

    async def upload_group_avatar(
        self: "rubigram.Client",
        object_guid: Any = None,
        path: str | Path = "",
        *,
        peer: Any = None,
        mime: str | None = None,
        progress: Callable[..., Any] | None = None,
        progress_args: tuple[Any, ...] = (),
    ) -> RawObject:
        file_path = Path(path)
        file_name = file_path.name
        file_size = file_path.stat().st_size
        file_mime = mime or self.guess_upload_mime(file_path)

        descriptor = await self.request_send_file(file_name=file_name, size=file_size, mime=file_mime)
        uploaded = await self.upload_file(
            path=file_path,
            descriptor=descriptor,
            progress=progress,
            progress_args=progress_args,
        )

        return await self.invoke(
            UploadNewGroupAvatar(
                group_guid=self._resolve_object_guid(object_guid, peer=peer),
                file_id=str(uploaded.id),
                dc_id=str(uploaded.dc_id),
                access_hash_rec=str(uploaded.access_hash_rec),
            )
        )

    async def set_group_photo(
        self: "rubigram.Client",
        object_guid: Any = None,
        path: str | Path = "",
        *,
        peer: Any = None,
        mime: str | None = None,
        progress: Callable[..., Any] | None = None,
        progress_args: tuple[Any, ...] = (),
    ) -> RawObject:
        return await self.upload_group_avatar(
            object_guid=object_guid,
            path=path,
            peer=peer,
            mime=mime,
            progress=progress,
            progress_args=progress_args,
        )
