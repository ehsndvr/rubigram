"""Users, profile and contacts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Sequence

from rubigram.errors import AuthError
from rubigram.raw.functions import build_updated_parameters
from rubigram.raw.methods import (
    AddAddressBook,
    CheckUserUsername,
    DeleteContact,
    GetAbsObjects,
    GetAvatars,
    GetBlockedUsers,
    GetCommonGroups,
    GetContacts,
    GetContactsLastOnline,
    GetContactsUpdates,
    GetObjectByUsername,
    GetProfileLinkItems,
    GetUserInfo,
    ReportObject,
    ResetContacts,
    SearchGlobalObjects,
    SetAskSpamAction,
    SetBlockUser,
    UpdateProfile,
    UpdateUsername,
)
from rubigram.types import (
    AbsObjects,
    BlockedUsers,
    ChatAvatars,
    CommonGroups,
    Contacts,
    ContactsLastOnline,
    ContactsUpdates,
    Empty,
    ObjectByUsername,
    ProfileLinkItems,
    RawObject,
    SearchGlobalObjectsResult,
    UpdatedProfile,
    UserInfo,
    UsernameCheck,
)

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client


class Users:
    async def get_me(self: "Client") -> Any:
        """The logged-in user (``getUserInfo`` on the stored guid) or the bot profile. [HTTP][bot]"""
        if self.is_bot:
            return await self._bot_get_me()
        user_guid = await self.storage.user_guid()
        if not user_guid:
            raise AuthError("No authenticated user_guid is available in the current session")
        return await self.get_user_info(user_guid)

    async def get_user_info(self: "Client", user_guid: Any) -> UserInfo:
        """``getUserInfo``. [HTTP]"""
        return await self.invoke(GetUserInfo(user_guid=self._resolve_user_guid(user_guid)))

    async def get_object_by_username(self: "Client", username: str) -> ObjectByUsername:
        """Resolve a ``@username`` to a user/group/channel/bot (``getObjectByUsername``). [HTTP]"""
        return await self.invoke(GetObjectByUsername(username=str(username).lstrip("@")))

    async def get_abs_objects(self: "Client", object_guids: Sequence[Any]) -> AbsObjects:
        """Minimal info (title, avatar, type) for up to 50 guids (``getAbsObjects``). [HTTP]"""
        return await self.invoke(GetAbsObjects(objects_guids=self._resolve_guids(object_guids)[:50]))

    async def get_avatars(self: "Client", object_guid: Any = None, *, peer: Any = None) -> ChatAvatars:
        """``getAvatars`` of a user, group or channel. [HTTP]"""
        return await self.invoke(GetAvatars(object_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def update_profile(self: "Client", *, first_name: Optional[str] = None, last_name: Optional[str] = None, bio: Optional[str] = None, birth_date: Optional[str] = None) -> UpdatedProfile:
        """Change name, bio or birth date (``updateProfile``). [HTTP]"""
        values, names = build_updated_parameters({"first_name": first_name, "last_name": last_name, "bio": bio, "birth_date": birth_date})
        if not names:
            raise ValueError("At least one profile field must be provided")
        return await self.invoke(UpdateProfile(updated_parameters=names, **values))

    async def update_username(self: "Client", username: str) -> UpdatedProfile:
        """``updateUsername``. [HTTP]"""
        return await self.invoke(UpdateUsername(username=str(username).lstrip("@")))

    async def check_username(self: "Client", username: str) -> UsernameCheck:
        """Whether a username is taken (``checkUserUsername``). [HTTP]"""
        return await self.invoke(CheckUserUsername(username=str(username).lstrip("@")))

    async def set_block_user(self: "Client", user_guid: Any, action: Any = "Block") -> RawObject:
        """``setBlockUser`` with ``Block`` / ``Unblock``. [HTTP]"""
        return await self.invoke(SetBlockUser(user_guid=self._resolve_user_guid(user_guid), action=str(getattr(action, "value", action))))

    async def block_user(self: "Client", object_guid: Any = None, *, peer: Any = None) -> RawObject:
        """Block a user (``setBlockUser`` / ``Block``). [HTTP]"""
        return await self.set_block_user(peer if peer is not None else object_guid, "Block")

    async def unblock_user(self: "Client", object_guid: Any = None, *, peer: Any = None) -> RawObject:
        """Unblock a user (``setBlockUser`` / ``Unblock``). [HTTP]"""
        return await self.set_block_user(peer if peer is not None else object_guid, "Unblock")

    async def get_blocked_users(self: "Client", start_id: Optional[str] = None) -> BlockedUsers:
        """``getBlockedUsers``. [HTTP]"""
        return await self.invoke(GetBlockedUsers(start_id=start_id))

    async def get_contacts(self: "Client", start_id: Optional[str] = None) -> Contacts:
        """A page of contacts (``getContacts``); pass ``next_start_id`` to continue. [HTTP]"""
        return await self.invoke(GetContacts(start_id=start_id))

    async def get_contacts_updates(self: "Client", state: Optional[int] = None) -> ContactsUpdates:
        """``getContactsUpdates`` since ``state`` (defaults to the stored contacts state). [HTTP]"""
        if state is None:
            state = await self.storage.contacts_state()
        if state is None:
            import time

            state = int(time.time())
        result = await self.invoke(GetContactsUpdates(state=state))
        if result.new_state is not None:
            await self.storage.set_contacts_state(result.new_state)
        return result

    async def get_contacts_last_online(self: "Client", user_guids: Sequence[Any]) -> ContactsLastOnline:
        """``getContactsLastOnline``. [HTTP]"""
        return await self.invoke(GetContactsLastOnline(user_guids=[self._resolve_user_guid(guid) for guid in user_guids]))

    async def add_contact(self: "Client", phone: str, first_name: str, last_name: str = "") -> UpdatedProfile:
        """Add a phone number to the address book (``addAddressBook``). [HTTP]"""
        from rubigram.utils import normalize_phone_number

        return await self.invoke(AddAddressBook(phone=normalize_phone_number(phone), first_name=first_name, last_name=last_name))

    async def delete_contact(self: "Client", user_guid: Any) -> Empty:
        """``deleteContact``. [HTTP]"""
        return await self.invoke(DeleteContact(user_guid=self._resolve_user_guid(user_guid)))

    async def reset_contacts(self: "Client") -> Empty:
        """``resetContacts``. [HTTP]"""
        return await self.invoke(ResetContacts())

    async def get_profile_link_items(self: "Client", object_guid: Any = None, *, peer: Any = None) -> ProfileLinkItems:
        """``getProfileLinkItems``. [HTTP]"""
        return await self.invoke(GetProfileLinkItems(object_guid=self._resolve_object_guid(object_guid, peer=peer)))

    async def get_common_groups(self: "Client", user_guid: Any) -> CommonGroups:
        """Groups shared with a user (``getCommonGroups``). [HTTP]"""
        return await self.invoke(GetCommonGroups(user_guid=self._resolve_user_guid(user_guid)))

    async def report_object(self: "Client", object_guid: Any, report_type: str, *, description: Optional[str] = None, message_id: Optional[str] = None, report_type_object: Optional[str] = None) -> Empty:
        """``reportObject``. [HTTP]"""
        return await self.invoke(ReportObject(object_guid=self._resolve_object_guid(object_guid), report_type=report_type, report_description=description, message_id=message_id, report_type_object=report_type_object))

    async def set_ask_spam_action(self: "Client", object_guid: Any, action: str) -> RawObject:
        """``setAskSpamAction``. [HTTP]"""
        return await self.invoke(SetAskSpamAction(object_guid=self._resolve_object_guid(object_guid), action=action))

    async def search_global_objects(self: "Client", search_text: str, filter_types: Sequence[Any] = ()) -> SearchGlobalObjectsResult:
        """Global search of users, groups, channels and bots (``searchGlobalObjects``). [HTTP]"""
        return await self.invoke(SearchGlobalObjects(search_text=search_text, filter_types=self._plain_list(filter_types) or None))

    search_global = search_global_objects


__all__ = ["Users"]
