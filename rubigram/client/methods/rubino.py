"""Rubino (posts and stories) and the services base info."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from rubigram.errors import LoginRequired, RubigramError
from rubigram.raw.methods import GetBaseInfo, GetProfilePosts, GetProfilesStoryList, SendRubinoPost
from rubigram.types import BaseInfo, RubinoPostsResult, RubinoStoriesResult, SentMessage

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client

log = logging.getLogger(__name__)


class Rubino:
    async def get_base_info(self: "Client") -> BaseInfo:
        """``getBaseInfo`` on the services base; stores the suggested Rubino/wallet URLs. [HTTP]"""
        self._require_user_session("get_base_info")
        if not await self.storage.auth():
            raise LoginRequired("This method requires an authenticated session")
        result = await self.invoke(GetBaseInfo())
        payload = result.to_dict()
        self.dc.update_from_base_info({"suggested_urls": payload.get("suggested_urls") or {}})
        await self.storage.set_dc_repository(self.dc.to_dict())
        await self.storage.set_suggested_urls(self.dc.suggested_urls or None)
        return result

    async def _ensure_base_info(self: "Client", force: bool = False) -> Optional[dict[str, str]]:
        if not force and self.dc.suggested_urls:
            return self.dc.suggested_urls
        if not await self.storage.auth():
            return None
        await self.get_base_info()
        return self.dc.suggested_urls or None

    async def get_rubino_post(self: "Client", post_id: Any = None, post_profile_id: Optional[str] = None, *, rubino_post_data: Any = None, track_id: Optional[str] = None) -> RubinoPostsResult:
        """Fetch one Rubino post (``getProfilePosts`` on the Rubino DC).

        Pass ``post_id`` and ``post_profile_id`` or ``rubino_post_data=message.rubino_post_data``.
        [HTTP]
        """
        self._require_user_session("get_rubino_post")
        resolved_post_id, resolved_profile_id = self._resolve_rubino_post_input(post_id=post_id, post_profile_id=post_profile_id, rubino_post_data=rubino_post_data)
        if not await self.storage.auth():
            raise LoginRequired("This method requires an authenticated session")
        if not self.dc.suggested_urls:
            try:
                await self._ensure_base_info()
            except RubigramError as exc:
                log.warning("Base info lookup failed, using the default Rubino DC: %s", exc)
        result = await self.invoke(GetProfilePosts(target_profile_id=resolved_profile_id, max_id=resolved_post_id, min_id=resolved_post_id, equal=True, limit=1, sort="FromMax"))
        if track_id is not None:
            result.track_id = track_id
        return result

    async def get_rubino_stories(self: "Client", story_id: str, story_profile_id: str) -> RubinoStoriesResult:
        """Fetch a story (``getProfilesStoryList`` on the Rubino DC). [HTTP]"""
        self._require_user_session("get_rubino_stories")
        if not self.dc.suggested_urls:
            try:
                await self._ensure_base_info()
            except RubigramError as exc:
                log.warning("Base info lookup failed, using the default Rubino DC: %s", exc)
        return await self.invoke(GetProfilesStoryList(profile_story_ids=[{"story_ids": [story_id], "profile_id": story_profile_id}]))

    async def send_rubino_post(self: "Client", object_guid: Any, post_id: str, post_profile_id: str, *, text: Optional[str] = None) -> SentMessage:
        """Share a Rubino post into a chat (``sendRubinoPost``). [HTTP]"""
        return await self.invoke(SendRubinoPost(object_guid=self._resolve_object_guid(object_guid), rnd=self._new_rnd(), post_id=post_id, post_profile_id=post_profile_id, text=text))

    @staticmethod
    def _resolve_rubino_post_input(*, post_id: Any, post_profile_id: Optional[str], rubino_post_data: Any) -> tuple[str, str]:
        source = rubino_post_data if rubino_post_data is not None else post_id
        if source is not None and not isinstance(source, str):
            nested = getattr(source, "rubino_post_data", None)
            if nested is not None:
                source = nested
        if source is not None and not isinstance(source, str):
            resolved_post_id = getattr(source, "post_id", None)
            resolved_profile_id = getattr(source, "post_profile_id", None)
            if resolved_post_id and resolved_profile_id:
                return str(resolved_post_id), str(resolved_profile_id)
        if not post_id or not post_profile_id:
            raise ValueError("Provide post_id and post_profile_id, or pass rubino_post_data/message.rubino_post_data")
        return str(post_id), str(post_profile_id)


__all__ = ["Rubino"]
