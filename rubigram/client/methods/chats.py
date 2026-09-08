"""Dialog list, seen state, chat actions and chat deletion."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Optional, Sequence

from rubigram.client.base import BaseClient
from rubigram.raw.methods import (
    ClickMessageUrl,
    DeleteBotChat,
    DeleteChatHistory,
    DeleteNoAccessGroupChat,
    DeleteServiceChat,
    DeleteUserChat,
    GetChatAds,
    GetChats,
    GetChatsByID,
    GetLinkFromAppUrl,
    GetLinkObject,
    GetMessageShareUrl,
    GetRelatedObjects,
    SeenChats,
    SetActionChat,
    SetChatUseTime,
)
from rubigram.types import Chat, ChatAdsResult, ChatsResult, DeleteChatHistoryResult, Empty, RawObject, ShareUrl


class Chats(BaseClient):
    async def get_chats(self, start_id: Optional[str] = None) -> ChatsResult:
        """One page of the dialog list (``getChats``); pass ``next_start_id`` to continue. [HTTP]"""
        return await self.invoke(GetChats(start_id=start_id))

    async def iter_chats(self, limit: Optional[int] = None) -> AsyncIterator[Chat]:
        """Iterate over every dialog, paging with ``getChats``. [HTTP]"""
        start_id: Optional[str] = None
        seen = 0
        while True:
            page = await self.get_chats(start_id)
            for chat in page.chats:
                yield chat
                seen += 1
                if limit is not None and seen >= limit:
                    return
            if not page.has_continue or not page.next_start_id:
                return
            start_id = page.next_start_id

    async def get_chats_by_id(self, object_guids: Sequence[Any]) -> ChatsResult:
        """``getChatsByID``. [HTTP]"""
        return await self.invoke(GetChatsByID(object_guids=self._resolve_guids(object_guids)))

    async def get_chat(self, object_guid: Any = None, *, peer: Any = None) -> Any:
        """One dialog (``getChatsByID``); for bots the Bot API ``getChat``. [HTTP][bot]"""
        guid = self._resolve_object_guid(object_guid, peer=peer)
        if self.is_bot:
            return await self._bot_get_chat(guid)
        result = await self.get_chats_by_id([guid])
        return result.chats[0] if result.chats else None

    async def seen_chats(self, seen_list: Dict[Any, Any]) -> Empty:
        """Mark messages as read: ``{object_guid: last_seen_message_id}`` (``seenChats``). [HTTP]"""
        return await self.invoke(
            SeenChats(seen_list={self._resolve_object_guid(guid): str(message_id) for guid, message_id in seen_list.items()})
        )

    async def seen(self, object_guid: Any, message_id: Any) -> Empty:
        """Mark one chat as read up to ``message_id``. [HTTP]"""
        return await self.seen_chats({object_guid: message_id})

    async def set_action_chat(self, object_guid: Any, action: Any, *, duration: Optional[int] = None) -> RawObject:
        """``setActionChat`` (``Mute``/``Unmute``/``Pin``/``Unpin``/``Archive``/``Unarchive``). [HTTP]"""
        return await self.invoke(
            SetActionChat(
                object_guid=self._resolve_object_guid(object_guid), action=str(getattr(action, "value", action)), duration=duration
            )
        )

    async def mute_chat(self, object_guid: Any, *, duration: Optional[int] = None) -> RawObject:
        """Mute a chat, optionally for ``duration`` seconds (``setActionChat`` / ``Mute``). [HTTP]"""
        return await self.set_action_chat(object_guid, "Mute", duration=duration)

    async def unmute_chat(self, object_guid: Any) -> RawObject:
        """Unmute a chat (``setActionChat`` / ``Unmute``). [HTTP]"""
        return await self.set_action_chat(object_guid, "Unmute")

    async def pin_chat(self, object_guid: Any) -> RawObject:
        """Pin a chat to the top of the list (``setActionChat`` / ``Pin``). [HTTP]"""
        return await self.set_action_chat(object_guid, "Pin")

    async def unpin_chat(self, object_guid: Any) -> RawObject:
        """Unpin a chat (``setActionChat`` / ``Unpin``). [HTTP]"""
        return await self.set_action_chat(object_guid, "Unpin")

    async def archive_chat(self, object_guid: Any) -> RawObject:
        """Move a chat to the archive (``setActionChat`` / ``Archive``). [HTTP]"""
        return await self.set_action_chat(object_guid, "Archive")

    async def unarchive_chat(self, object_guid: Any) -> RawObject:
        """Move a chat out of the archive (``setActionChat`` / ``Unarchive``). [HTTP]"""
        return await self.set_action_chat(object_guid, "Unarchive")

    async def set_chat_use_time(self, object_guid: Any, time: int) -> Empty:
        """Record when a chat was last opened (``setChatUseTime``). [HTTP]"""
        return await self.invoke(SetChatUseTime(object_guid=self._resolve_object_guid(object_guid), time=int(time)))

    async def delete_user_chat(self, user_guid: Any, last_deleted_message_id: Any = "0") -> RawObject:
        """Delete a private chat (``deleteUserChat``). [HTTP]"""
        return await self.invoke(
            DeleteUserChat(user_guid=self._resolve_user_guid(user_guid), last_deleted_message_id=str(last_deleted_message_id))
        )

    async def delete_chat_history(self, object_guid: Any = None, last_message_id: Any = "", *, peer: Any = None) -> DeleteChatHistoryResult:
        """Clear the local history up to ``last_message_id`` (``deleteChatHistory``). [HTTP]"""
        return await self.invoke(
            DeleteChatHistory(object_guid=self._resolve_object_guid(object_guid, peer=peer), last_message_id=str(last_message_id))
        )

    async def delete_bot_chat(self, bot_guid: Any, last_deleted_message_id: Any = "0") -> RawObject:
        """Delete the chat with a bot (``deleteBotChat``). [HTTP]"""
        return await self.invoke(
            DeleteBotChat(bot_guid=self._resolve_object_guid(bot_guid), last_deleted_message_id=str(last_deleted_message_id))
        )

    async def delete_service_chat(self, service_guid: Any, last_deleted_message_id: Any = "0") -> RawObject:
        """Delete a service chat (``deleteServiceChat``). [HTTP]"""
        return await self.invoke(
            DeleteServiceChat(service_guid=self._resolve_object_guid(service_guid), last_deleted_message_id=str(last_deleted_message_id))
        )

    async def delete_no_access_group_chat(self, group_guid: Any) -> RawObject:
        """Remove a group you can no longer access from the list (``deleteNoAccessGroupChat``). [HTTP]"""
        return await self.invoke(DeleteNoAccessGroupChat(group_guid=self._resolve_object_guid(group_guid)))

    async def get_chat_ads(self, state: Optional[int] = None) -> ChatAdsResult:
        """Sponsored entries for the chat list (``getChatAds``). [HTTP]"""
        return await self.invoke(GetChatAds(state=state))

    async def get_related_objects(self, object_guid: Any, start_id: Optional[str] = None) -> RawObject:
        """Related chats suggested for an object (``getRelatedObjects``). [HTTP]"""
        return await self.invoke(GetRelatedObjects(object_guid=self._resolve_object_guid(object_guid), start_id=start_id))

    async def click_message_url(self, object_guid: Any, message_id: Any, link_url: str) -> Empty:
        """Report a click on a link inside a message (``clickMessageUrl``). [HTTP]"""
        return await self.invoke(
            ClickMessageUrl(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id), link_url=link_url)
        )

    async def get_message_share_url(self, object_guid: Any, message_id: Any) -> ShareUrl:
        """Public link of a channel message (``getMessageShareUrl``). [HTTP]"""
        return await self.invoke(GetMessageShareUrl(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id)))

    async def get_link_from_app_url(self, app_url: str) -> RawObject:
        """Resolve an in-app URL (``getLinkFromAppUrl``). [HTTP]"""
        return await self.invoke(GetLinkFromAppUrl(app_url=app_url))

    async def get_link_object(self, share_string: str) -> RawObject:
        """Resolve a ``rubika.ir`` share string (``getlinkObject``). [HTTP]"""
        return await self.invoke(GetLinkObject(share_string=share_string))


__all__ = ["Chats"]
