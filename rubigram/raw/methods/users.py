from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from rubigram.raw.base import RawMethod
from rubigram.types import ChatAvatars, ObjectByUsername, RawObject, UserInfo

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
