"""Group models and results."""

from __future__ import annotations

from typing import Any, Optional

from .chat import Chat, ChatUpdate
from .files import AvatarThumbnail
from .message import MessageUpdate
from .object import Object, model
from .user import OnlineTime, PeerObject


@model
class ChatReactionSetting(Object):
    reaction_type: Optional[str] = None
    selected_reactions: list[str] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.selected_reactions = self.selected_reactions or []


@model
class Group(Object):
    group_guid: Optional[str] = None
    group_title: Optional[str] = None
    description: Optional[str] = None
    avatar_thumbnail: Optional[AvatarThumbnail] = None
    count_members: Optional[int] = None
    is_deleted: Optional[bool] = None
    is_verified: Optional[bool] = None
    slow_mode: Optional[int] = None
    chat_history_for_new_members: Optional[str] = None
    event_messages: Optional[bool] = None
    chat_reaction_setting: Optional[ChatReactionSetting] = None
    is_restricted_content: Optional[bool] = None
    group_type: Optional[str] = None
    is_join_request_active: Optional[bool] = None

    @property
    def title(self) -> Optional[str]:
        return self.group_title

    async def leave(self) -> Any:
        if self._client is None or not self.group_guid:
            raise RuntimeError("This group is not bound to a Client instance")
        return await self._client.leave_group(self.group_guid)


@model
class GroupMember(Object):
    member_type: Optional[str] = None
    member_guid: Optional[str] = None
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_verified: Optional[bool] = None
    is_deleted: Optional[bool] = None
    last_online: Optional[int] = None
    join_type: Optional[str] = None
    online_time: Optional[OnlineTime] = None
    avatar_thumbnail: Optional[AvatarThumbnail] = None
    promoted_by_object_guid: Optional[str] = None


@model
class GroupMembers(Object):
    """Result of the ``get*Members`` methods (groups and channels)."""

    in_chat_members: list[GroupMember] = None  # type: ignore[assignment]
    next_start_id: Optional[str] = None
    has_continue: Optional[bool] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.in_chat_members = self.in_chat_members or []

    def __iter__(self):
        return iter(self.in_chat_members)

    def __len__(self) -> int:
        return len(self.in_chat_members)


@model
class GroupInfo(Object):
    group: Optional[Group] = None
    chat: Optional[Chat] = None
    timestamp: Optional[str] = None


@model
class GroupDefaultAccess(Object):
    access_list: list[str] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.access_list = self.access_list or []


AdminAccessList = GroupDefaultAccess


@model
class PendingObjectOwner(Object):
    exist_pending_owner: Optional[bool] = None
    pending_owner: Optional[PeerObject] = None


@model
class GroupLink(Object):
    join_link: Optional[str] = None


@model
class JoinLinkObject(Object):
    type: Optional[str] = None
    object_guid: Optional[str] = None


@model
class JoinLinkEntry(Object):
    object_guid: Optional[JoinLinkObject] = None
    join_link: Optional[str] = None
    creator_guid: Optional[str] = None
    create_time: Optional[int] = None
    request_pending_count: Optional[int] = None
    request_needed: Optional[bool] = None
    usage_limit: Optional[int] = None
    usage_count: Optional[int] = None
    title: Optional[str] = None
    expire_time: Optional[int] = None
    expire_at: Optional[int] = None
    is_revoked: Optional[bool] = None


@model
class JoinLinks(Object):
    join_links: list[Any] = None  # type: ignore[assignment]
    revoked_join_links: list[Any] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.join_links = self.join_links or []
        self.revoked_join_links = self.revoked_join_links or []


@model
class CreatedJoinLink(Object):
    join_link: Optional[JoinLinkEntry] = None


@model
class JoinRequest(Object):
    user: Optional[PeerObject] = None
    user_guid: Optional[str] = None
    request_time: Optional[int] = None
    join_link: Optional[str] = None


@model
class JoinRequests(Object):
    join_requests: list[Any] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.join_requests = self.join_requests or []


@model
class AddGroupResult(Object):
    group: Optional[Group] = None
    chat_update: Optional[ChatUpdate] = None
    message_update: Optional[MessageUpdate] = None
    timestamp: Optional[str] = None


@model
class EditGroupInfoResult(Object):
    group: Optional[Group] = None
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None


@model
class BanGroupMemberResult(Object):
    timestamp: Optional[str] = None
    group: Optional[Group] = None
    chat_update: Optional[ChatUpdate] = None


@model
class SetGroupAdminResult(Object):
    in_chat_member: Optional[GroupMember] = None
    timestamp: Optional[str] = None


@model
class AddGroupMembersResult(Object):
    group: Optional[Group] = None
    added_in_chat_members: list[GroupMember] = None  # type: ignore[assignment]
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.added_in_chat_members = self.added_in_chat_members or []


@model
class GroupPreview(Object):
    """Result of ``groupPreviewByJoinLink``."""

    is_valid: Optional[bool] = None
    group: Optional[Group] = None
    is_member: Optional[bool] = None
    has_join_request: Optional[bool] = None
    timestamp: Optional[str] = None


@model
class JoinedGroup(Object):
    """Result of ``joinGroup``."""

    group: Optional[Group] = None
    chat_update: Optional[ChatUpdate] = None
    message_update: Optional[MessageUpdate] = None
    is_valid: Optional[bool] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None


@model
class GroupOnlineCount(Object):
    online_count: Optional[int] = None


@model
class MentionList(Object):
    in_chat_members: list[GroupMember] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.in_chat_members = self.in_chat_members or []


@model
class OwnerRequestResult(Object):
    status: Optional[str] = None
    chat_update: Optional[ChatUpdate] = None
    timestamp: Optional[str] = None


__all__ = [
    "AddGroupMembersResult",
    "AddGroupResult",
    "AdminAccessList",
    "BanGroupMemberResult",
    "ChatReactionSetting",
    "CreatedJoinLink",
    "EditGroupInfoResult",
    "Group",
    "GroupDefaultAccess",
    "GroupInfo",
    "GroupLink",
    "GroupMember",
    "GroupMembers",
    "GroupOnlineCount",
    "GroupPreview",
    "JoinLinkEntry",
    "JoinLinkObject",
    "JoinLinks",
    "JoinRequest",
    "JoinRequests",
    "JoinedGroup",
    "MentionList",
    "OwnerRequestResult",
    "PendingObjectOwner",
    "SetGroupAdminResult",
]
