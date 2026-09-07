"""Join links and join requests (groups and channels)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from rubigram.raw.functions import build_updated_parameters
from rubigram.raw.methods import (
    ActionOnJoinRequest,
    CreateJoinLink,
    DeleteRevokedJoinLink,
    EditJoinLink,
    GetJoinLinks,
    GetJoinLinkUserJoined,
    GetJoinRequests,
    RevokeJoinLink,
)
from rubigram.types import CreatedJoinLink, JoinLinks, JoinRequests, RawObject

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client


class JoinLinksMixin:
    async def get_join_links(self: "Client", object_guid: Any = None, *, peer: Any = None, creator_guid: Any = None) -> JoinLinks:
        """``getJoinLinks`` of a group or channel. [HTTP]"""
        return await self.invoke(GetJoinLinks(object_guid=self._resolve_object_guid(object_guid, peer=peer), creator_guid=self._resolve_user_guid(creator_guid) if creator_guid else None))

    async def create_join_link(self: "Client", object_guid: Any = None, title: str = "", *, peer: Any = None, request_needed: bool = False, expire_time: int = 0, usage_limit: int = 0) -> CreatedJoinLink:
        """``createJoinLink``. [HTTP]"""
        return await self.invoke(CreateJoinLink(object_guid=self._resolve_object_guid(object_guid, peer=peer), title=title, request_needed=request_needed, expire_time=int(expire_time), usage_limit=int(usage_limit)))

    async def edit_join_link(self: "Client", object_guid: Any, join_link: str, *, title: Optional[str] = None, request_needed: Optional[bool] = None, expire_time: Optional[int] = None, usage_limit: Optional[int] = None) -> CreatedJoinLink:
        """``editJoinLink``; only the given fields are updated. [HTTP]"""
        values, names = build_updated_parameters({"title": title, "request_needed": request_needed, "expire_time": expire_time, "usage_limit": usage_limit})
        if not names:
            raise ValueError("At least one join link field must be provided")
        return await self.invoke(EditJoinLink(object_guid=self._resolve_object_guid(object_guid), join_link=join_link, updated_parameters=names, **values))

    async def revoke_join_link(self: "Client", object_guid: Any, join_link: str) -> RawObject:
        return await self.invoke(RevokeJoinLink(object_guid=self._resolve_object_guid(object_guid), join_link=join_link))

    async def delete_revoked_join_link(self: "Client", object_guid: Any, join_link: Optional[str] = None) -> RawObject:
        return await self.invoke(DeleteRevokedJoinLink(object_guid=self._resolve_object_guid(object_guid), join_link=join_link))

    async def get_join_requests(self: "Client", object_guid: Any, start_id: Optional[str] = None) -> JoinRequests:
        return await self.invoke(GetJoinRequests(object_guid=self._resolve_object_guid(object_guid), start_id=start_id))

    async def action_on_join_request(self: "Client", object_guid: Any, user_guid: Any, action: Any) -> RawObject:
        """``actionOnJoinRequest`` (``Accept`` / ``Reject``). [HTTP]"""
        return await self.invoke(ActionOnJoinRequest(object_guid=self._resolve_object_guid(object_guid), user_guid=self._resolve_user_guid(user_guid), action=str(getattr(action, "value", action))))

    async def accept_join_request(self: "Client", object_guid: Any, user_guid: Any) -> RawObject:
        return await self.action_on_join_request(object_guid, user_guid, "Accept")

    async def reject_join_request(self: "Client", object_guid: Any, user_guid: Any) -> RawObject:
        return await self.action_on_join_request(object_guid, user_guid, "Reject")

    async def get_join_link_user_joined(self: "Client", object_guid: Any, join_link: str, start_id: Optional[str] = None) -> RawObject:
        return await self.invoke(GetJoinLinkUserJoined(object_guid=self._resolve_object_guid(object_guid), join_link=join_link, start_id=start_id))


__all__ = ["JoinLinksMixin"]
