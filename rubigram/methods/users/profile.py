from __future__ import annotations

from typing import Any, Sequence

import rubigram
from rubigram.raw.methods import GetAvatars, GetContacts, GetContactsLastOnline, GetObjectByUsername, GetProfileLinkItems, GetUserInfo
from rubigram.types import ChatAvatars, ContactsLastOnline, ObjectByUsername, ProfileLinkItems, RawObject, UserInfo


class UserProfile:
    async def get_user_info(self: "rubigram.Client", user_guid: Any) -> UserInfo:
        return await self.invoke(GetUserInfo(user_guid=self._resolve_user_guid(user_guid)))

    async def get_me(self: "rubigram.Client") -> Any:
        if self.is_bot:
            data = await self._invoke_bot("getMe")
            if isinstance(data, dict) and "bot" in data:
                data = data["bot"]
            from rubigram.bot.types import Bot

            return Bot._parse(self, data)

        user_guid = await self.storage.user_guid()
        if not user_guid:
            from rubigram.exceptions import AuthError

            raise AuthError("No authenticated user_guid is available in the current session")
        return await self.get_user_info(user_guid)

    async def get_object_by_username(self: "rubigram.Client", username: str) -> ObjectByUsername:
        return await self.invoke(GetObjectByUsername(username=username))

    async def get_avatars(self: "rubigram.Client", object_guid: Any = None, *, peer: Any = None) -> ChatAvatars:
        return await self.invoke(GetAvatars(object_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_contacts(self: "rubigram.Client", offset: int = 0, limit: int = 100) -> RawObject:
        return await self.invoke(GetContacts(offset=offset, limit=limit))

    async def get_contacts_last_online(self: "rubigram.Client", user_guids: Sequence[Any]) -> ContactsLastOnline:
        return await self.invoke(
            GetContactsLastOnline(
                user_guids=[self._resolve_user_guid(user_guid) for user_guid in user_guids],
            )
        )

    async def get_profile_link_items(self: "rubigram.Client", object_guid: Any = None, *, peer: Any = None) -> ProfileLinkItems:
        return await self.invoke(GetProfileLinkItems(object_guid=self._resolve_object_guid(object_guid, peer=peer)))
