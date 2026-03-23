from __future__ import annotations

from typing import Any, Sequence

import rubigram
from rubigram.raw.methods import AddChannel, GetChannelAllMembers, GetChannelInfo, GetChannelLink
from rubigram.types import AddChannelResult, ChannelInfo, Empty, GroupMembers


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
