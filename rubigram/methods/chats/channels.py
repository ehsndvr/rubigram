from __future__ import annotations

from typing import Any, Sequence

import rubigram
from rubigram.raw.methods import AddChannel, AddChannelMembers, EditChannelInfo, GetBannedChannelMembers, GetChannelAdminMembers, GetChannelAllMembers, GetChannelInfo, GetChannelLink, SetChannelAdmin
from rubigram.types import AddChannelMembersResult, AddChannelResult, ChannelInfo, EditChannelInfoResult, Empty, GroupMembers, SetGroupAdminResult


class Channels:
    async def add_channel(
        self: "rubigram.Client",
        title: str,
        description: str = "",
        channel_type: str = "Private",
        member_guids: Sequence[Any] | None = None,
        *,
        thumbnail_file_id: str,
        main_file_id: str,
    ) -> AddChannelResult:
        resolved_members = [self._resolve_object_guid(member) for member in member_guids or ()]
        return await self.invoke(
            AddChannel(
                title=title,
                description=description,
                channel_type=channel_type,
                member_guids=resolved_members,
                thumbnail_file_id=thumbnail_file_id,
                main_file_id=main_file_id,
            )
        )

    async def create_channel(
        self: "rubigram.Client",
        title: str,
        description: str = "",
        channel_type: str = "Private",
        member_guids: Sequence[Any] | None = None,
        *,
        thumbnail_file_id: str,
        main_file_id: str,
    ) -> AddChannelResult:
        return await self.add_channel(
            title=title,
            description=description,
            channel_type=channel_type,
            member_guids=member_guids,
            thumbnail_file_id=thumbnail_file_id,
            main_file_id=main_file_id,
        )

    async def add_channel_members(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guids: Sequence[Any] | None = None,
        *,
        peer: Any = None,
    ) -> AddChannelMembersResult:
        resolved_members = [self._resolve_object_guid(member) for member in member_guids or ()]
        return await self.invoke(
            AddChannelMembers(
                channel_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guids=resolved_members,
            )
        )

    async def get_channel_link(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> Empty:
        return await self.invoke(GetChannelLink(channel_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_channel_info(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> ChannelInfo:
        return await self.invoke(GetChannelInfo(channel_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_channel_all_members(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> GroupMembers:
        return await self.invoke(GetChannelAllMembers(channel_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_channel_admin_members(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> GroupMembers:
        return await self.invoke(GetChannelAdminMembers(channel_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_banned_channel_members(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
    ) -> GroupMembers:
        return await self.invoke(GetBannedChannelMembers(channel_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def set_channel_admin(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        access_list: Sequence[Any] = (),
        *,
        peer: Any = None,
    ) -> SetGroupAdminResult:
        return await self.invoke(
            SetChannelAdmin(
                channel_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guid=self._resolve_object_guid(member_guid),
                action="SetAdmin",
                access_list=self._normalize_group_access_list(access_list),
            )
        )

    async def update_channel_admin_access(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        access_list: Sequence[Any] = (),
        *,
        peer: Any = None,
    ) -> SetGroupAdminResult:
        return await self.set_channel_admin(object_guid, member_guid, access_list, peer=peer)

    async def unset_channel_admin(
        self: "rubigram.Client",
        object_guid: Any = None,
        member_guid: Any = None,
        *,
        peer: Any = None,
    ) -> SetGroupAdminResult:
        return await self.invoke(
            SetChannelAdmin(
                channel_guid=self._resolve_object_guid(object_guid, peer=peer),
                member_guid=self._resolve_object_guid(member_guid),
                action="UnsetAdmin",
                access_list=[],
            )
        )

    async def edit_channel_info(
        self: "rubigram.Client",
        object_guid: Any = None,
        *,
        peer: Any = None,
        title: str | None = None,
        description: str | None = None,
    ) -> EditChannelInfoResult:
        updated_parameters: list[str] = []
        if title is not None:
            updated_parameters.append("title")
        if description is not None:
            updated_parameters.append("description")
        if not updated_parameters:
            raise ValueError("At least one supported channel field must be provided")
        return await self.invoke(
            EditChannelInfo(
                channel_guid=self._resolve_object_guid(object_guid, peer=peer),
                updated_parameters=updated_parameters,
                title=title,
                description=description,
            )
        )
