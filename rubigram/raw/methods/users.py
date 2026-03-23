from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from rubigram.raw.base import RawMethod
from rubigram.types import ChatAvatars, ContactsLastOnline, ObjectByUsername, ProfileLinkItems, RawObject, UserInfo

if TYPE_CHECKING:
    import rubigram


@dataclass
class GetUserInfo(RawMethod[UserInfo]):
    """
    Get detailed information about a user.

    Requires authentication.
    """
    user_guid: str

    method_name = "getUserInfo"

    def to_input(self) -> Dict[str, Any]:
        return {
            "user_guid": self.user_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> UserInfo:
        return UserInfo._parse(client, data)


@dataclass
class GetObjectByUsername(RawMethod[ObjectByUsername]):
    """
    Get a user or chat object by its username.

    Requires authentication.
    """
    username: str

    method_name = "getObjectByUsername"

    def to_input(self) -> Dict[str, Any]:
        return {
            "username": self.username,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> ObjectByUsername:
        return ObjectByUsername._parse(client, data)


@dataclass
class GetAvatars(RawMethod[ChatAvatars]):
    """
    Get avatar images for a user or chat.

    Requires authentication.
    """
    object_guid: str

    method_name = "getAvatars"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> ChatAvatars:
        return ChatAvatars._parse(client, data)


@dataclass
class BlockUser(RawMethod[RawObject]):
    """
    Block a user.

    Requires authentication.
    """
    object_guid: str

    method_name = "blockUser"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
        }


@dataclass
class UnblockUser(RawMethod[RawObject]):
    """
    Unblock a user.

    Requires authentication.
    """
    object_guid: str

    method_name = "unblockUser"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
        }


@dataclass
class GetContacts(RawMethod[RawObject]):
    """
    Get the user's contact list.

    Requires authentication.
    """
    offset: int = 0
    limit: int = 100

    method_name = "getContacts"

    def to_input(self) -> Dict[str, Any]:
        return {
            "offset": self.offset,
            "limit": self.limit,
        }


@dataclass
class GetContactsLastOnline(RawMethod[ContactsLastOnline]):
    """
    Get last-online data for multiple users.

    Requires authentication.
    """

    user_guids: list[str]

    method_name = "getContactsLastOnline"

    def to_input(self) -> Dict[str, Any]:
        return {
            "user_guids": self.user_guids,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> ContactsLastOnline:
        return ContactsLastOnline._parse(client, data)


@dataclass
class GetProfileLinkItems(RawMethod[ProfileLinkItems]):
    """
    Get profile link items for a user or chat object.

    Requires authentication.
    """

    object_guid: str

    method_name = "getProfileLinkItems"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> ProfileLinkItems:
        return ProfileLinkItems._parse(client, data)
