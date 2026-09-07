"""User, contact and abstract-object models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .files import AvatarThumbnail
from .object import Object, model
from .raw_object import RawObject

if TYPE_CHECKING:  # pragma: no cover
    from .chat import Chat


@model
class OnlineTime(Object):
    type: Optional[str] = None
    approximate_period: Optional[str] = None
    exact_time: Optional[int] = None


@model
class PeerObject(Object):
    """An abstract object (``abs_object``): the minimal description of any chat."""

    object_guid: Optional[str] = None
    type: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    username: Optional[str] = None
    avatar_thumbnail: Optional[AvatarThumbnail] = None
    is_verified: Optional[bool] = None
    is_deleted: Optional[bool] = None
    count_members: Optional[int] = None

    @property
    def display_name(self) -> str:
        if self.title:
            return self.title
        return " ".join(part for part in (self.first_name, self.last_name) if part) or (self.username or self.object_guid or "")


@model
class User(Object):
    user_guid: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    last_online: Optional[int] = None
    is_deleted: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_bot: Optional[bool] = None
    online_time: Optional[OnlineTime] = None
    avatar_thumbnail: Optional[AvatarThumbnail] = None

    @property
    def full_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part)

    @property
    def mention(self) -> str:
        return f"@{self.username}" if self.username else self.full_name

    async def block(self) -> Any:
        if self._client is None or not self.user_guid:
            raise RuntimeError("This user is not bound to a Client instance")
        return await self._client.block_user(self.user_guid)

    async def unblock(self) -> Any:
        if self._client is None or not self.user_guid:
            raise RuntimeError("This user is not bound to a Client instance")
        return await self._client.unblock_user(self.user_guid)

    async def send_message(self, text: str, **kwargs: Any) -> Any:
        if self._client is None or not self.user_guid:
            raise RuntimeError("This user is not bound to a Client instance")
        return await self._client.send_message(self.user_guid, text=text, **kwargs)


@model
class UserAdditionalInfo(Object):
    is_in_contact: Optional[bool] = None
    can_receive_call: Optional[bool] = None
    can_video_call: Optional[bool] = None
    registration_time: Optional[int] = None
    country_code: Optional[str] = None
    official_info_text: Optional[str] = None


@model
class UserInfo(Object):
    """Result of ``getUserInfo``."""

    user: Optional[User] = None
    chat: Optional[Chat] = None
    timestamp: Optional[str] = None
    is_in_contact: Optional[bool] = None
    can_receive_call: Optional[bool] = None
    can_video_call: Optional[bool] = None
    user_additional_info: Optional[UserAdditionalInfo] = None


@model
class ContactsLastOnline(Object):
    users: list[User] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        if self.users is None:
            self.users = []


@model
class ContactsUpdates(Object):
    users: list[User] = None  # type: ignore[assignment]
    deleted_users: list[str] = None  # type: ignore[assignment]
    new_state: Optional[int] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.users = self.users or []
        self.deleted_users = self.deleted_users or []


@model
class Contacts(Object):
    """Result of ``getContacts``."""

    users: list[User] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None
    state: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.users = self.users or []


@model
class BlockedUsers(Object):
    abs_users: list[PeerObject] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.abs_users = self.abs_users or []


@model
class ObjectByUsername(Object):
    exist: Optional[bool] = None
    type: Optional[str] = None
    user: Optional[User] = None
    chat: Optional[Chat] = None
    channel: Optional[Any] = None
    group: Optional[Any] = None
    bot: Optional[Any] = None
    timestamp: Optional[str] = None
    is_in_contact: Optional[bool] = None

    @property
    def object_guid(self) -> Optional[str]:
        if self.chat is not None and getattr(self.chat, "object_guid", None):
            return self.chat.object_guid
        for holder in (self.user, self.channel, self.group, self.bot):
            if holder is None:
                continue
            for key in ("user_guid", "channel_guid", "group_guid", "bot_guid", "object_guid"):
                value = getattr(holder, key, None)
                if value:
                    return value
        return None


@model
class AbsObjects(Object):
    """Result of ``getAbsObjects``."""

    objects: list[PeerObject] = None  # type: ignore[assignment]
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.objects = self.objects or []


@model
class CommonGroups(Object):
    abs_groups: list[PeerObject] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.abs_groups = self.abs_groups or []


@model
class UsernameCheck(Object):
    exist: Optional[bool] = None
    username: Optional[str] = None


@model
class UpdatedProfile(Object):
    user: Optional[User] = None
    chat_update: Optional[Any] = None
    timestamp: Optional[str] = None


@model
class SentCode(Object):
    phone_code_hash: Optional[str] = None
    status: Optional[str] = None
    code_digits_count: Optional[int] = None
    has_confirmed_recovery_email: Optional[bool] = None
    no_recovery_alert: Optional[str] = None
    send_type: Optional[str] = None
    hint: Optional[str] = None


@model
class Authorization(Object):
    status: Optional[str] = None
    auth: Optional[str] = None
    user: Optional[User] = None
    user_guid: Optional[str] = None
    timestamp: Optional[str] = None
    two_step_status: Optional[Any] = None
    hint: Optional[str] = None


@model
class InlineOpenUrlData(Object):
    title: Optional[str] = None
    url: Optional[str] = None


@model
class ProfileLink(Object):
    type: Optional[str] = None
    inline_open_url_data: Optional[InlineOpenUrlData] = None


@model
class ProfileLinkItem(Object):
    title: Optional[str] = None
    link: Optional[ProfileLink] = None


@model
class ProfileLinkItems(Object):
    link_items: list[ProfileLinkItem] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.link_items = self.link_items or []


@model
class SearchGlobalObject(Object):
    object_guid: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    avatar_thumbnail: Optional[AvatarThumbnail] = None
    is_verified: Optional[bool] = None
    is_deleted: Optional[bool] = None
    count_members: Optional[int] = None
    username: Optional[str] = None
    track_id: Optional[str] = None


@model
class SearchGlobalObjectsResult(Object):
    objects: list[SearchGlobalObject] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.objects = self.objects or []


@model
class TimeResult(Object):
    time: Optional[int] = None


__all__ = [
    "AbsObjects",
    "Authorization",
    "BlockedUsers",
    "CommonGroups",
    "Contacts",
    "ContactsLastOnline",
    "ContactsUpdates",
    "InlineOpenUrlData",
    "ObjectByUsername",
    "OnlineTime",
    "PeerObject",
    "ProfileLink",
    "ProfileLinkItem",
    "ProfileLinkItems",
    "RawObject",
    "SearchGlobalObject",
    "SearchGlobalObjectsResult",
    "SentCode",
    "TimeResult",
    "UpdatedProfile",
    "User",
    "UserAdditionalInfo",
    "UserInfo",
    "UsernameCheck",
]
