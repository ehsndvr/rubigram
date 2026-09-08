"""User, profile and contact RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rubigram.raw.base import RawMethod
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
    SearchGlobalObjectsResult,
    UpdatedProfile,
    UserInfo,
    UsernameCheck,
)


@dataclass
class GetUserInfo(RawMethod[UserInfo]):
    user_guid: str

    method_name = "getUserInfo"
    result = UserInfo


@dataclass
class GetObjectByUsername(RawMethod[ObjectByUsername]):
    username: str

    method_name = "getObjectByUsername"
    result = ObjectByUsername


@dataclass
class GetAbsObjects(RawMethod[AbsObjects]):
    objects_guids: List[str]

    method_name = "getAbsObjects"
    result = AbsObjects


@dataclass
class GetAvatars(RawMethod[ChatAvatars]):
    object_guid: str

    method_name = "getAvatars"
    result = ChatAvatars


@dataclass
class UpdateProfile(RawMethod[UpdatedProfile]):
    updated_parameters: List[str]
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    birth_date: Optional[str] = None

    method_name = "updateProfile"
    result = UpdatedProfile


@dataclass
class UpdateUsername(RawMethod[UpdatedProfile]):
    username: str

    method_name = "updateUsername"
    result = UpdatedProfile


@dataclass
class CheckUserUsername(RawMethod[UsernameCheck]):
    username: str

    method_name = "checkUserUsername"
    result = UsernameCheck


@dataclass
class SetBlockUser(RawMethod[Any]):
    user_guid: str
    action: str = "Block"

    method_name = "setBlockUser"


@dataclass
class BlockUser(SetBlockUser):
    """rubigram 0.1 name: ``setBlockUser`` with ``action=Block``."""

    def __init__(self, object_guid: Optional[str] = None, *, user_guid: Optional[str] = None):
        super().__init__(user_guid=user_guid or object_guid or "", action="Block")


@dataclass
class UnblockUser(SetBlockUser):
    """rubigram 0.1 name: ``setBlockUser`` with ``action=Unblock``."""

    def __init__(self, object_guid: Optional[str] = None, *, user_guid: Optional[str] = None):
        super().__init__(user_guid=user_guid or object_guid or "", action="Unblock")


@dataclass
class GetBlockedUsers(RawMethod[BlockedUsers]):
    start_id: Optional[str] = None

    method_name = "getBlockedUsers"
    result = BlockedUsers


@dataclass
class GetContacts(RawMethod[Contacts]):
    start_id: Optional[str] = None

    method_name = "getContacts"
    result = Contacts


@dataclass
class GetContactsUpdates(RawMethod[ContactsUpdates]):
    state: int

    method_name = "getContactsUpdates"
    result = ContactsUpdates


@dataclass
class GetContactsLastOnline(RawMethod[ContactsLastOnline]):
    user_guids: List[str]

    method_name = "getContactsLastOnline"
    result = ContactsLastOnline


@dataclass
class AddAddressBook(RawMethod[UpdatedProfile]):
    phone: str
    first_name: str
    last_name: str = ""

    method_name = "addAddressBook"
    result = UpdatedProfile


@dataclass
class DeleteContact(RawMethod[Empty]):
    user_guid: str

    method_name = "deleteContact"
    result = Empty


@dataclass
class ResetContacts(RawMethod[Empty]):
    method_name = "resetContacts"
    result = Empty


@dataclass
class GetProfileLinkItems(RawMethod[ProfileLinkItems]):
    object_guid: str

    method_name = "getProfileLinkItems"
    result = ProfileLinkItems


@dataclass
class GetCommonGroups(RawMethod[CommonGroups]):
    user_guid: str

    method_name = "getCommonGroups"
    result = CommonGroups


@dataclass
class SearchGlobalObjects(RawMethod[SearchGlobalObjectsResult]):
    search_text: str
    filter_types: Optional[List[str]] = None

    method_name = "searchGlobalObjects"
    result = SearchGlobalObjectsResult

    def to_input(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"search_text": self.search_text}
        if self.filter_types:
            data["filter_types"] = list(self.filter_types)
        return data


@dataclass
class ReportObject(RawMethod[Empty]):
    object_guid: str
    report_type: str
    report_description: Optional[str] = None
    report_type_object: Optional[str] = None
    message_id: Optional[str] = None

    method_name = "reportObject"
    result = Empty


@dataclass
class SetAskSpamAction(RawMethod[Any]):
    object_guid: str
    action: str

    method_name = "setAskSpamAction"


__all__ = [
    "AddAddressBook",
    "BlockUser",
    "CheckUserUsername",
    "DeleteContact",
    "GetAbsObjects",
    "GetAvatars",
    "GetBlockedUsers",
    "GetCommonGroups",
    "GetContacts",
    "GetContactsLastOnline",
    "GetContactsUpdates",
    "GetObjectByUsername",
    "GetProfileLinkItems",
    "GetUserInfo",
    "ReportObject",
    "ResetContacts",
    "SearchGlobalObjects",
    "SetAskSpamAction",
    "SetBlockUser",
    "UnblockUser",
    "UpdateProfile",
    "UpdateUsername",
]
