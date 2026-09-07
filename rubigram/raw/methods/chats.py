"""Dialog-level RPCs (chat list, seen, chat actions, deletion, links)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import ChatAdsResult, ChatsResult, ChatsUpdates, DeleteChatHistoryResult, Empty, ShareUrl


@dataclass
class GetChats(RawMethod[ChatsResult]):
    start_id: Optional[str] = None

    method_name = "getChats"
    result = ChatsResult


@dataclass
class GetChatsUpdates(RawMethod[ChatsUpdates]):
    state: int

    method_name = "getChatsUpdates"
    result = ChatsUpdates


@dataclass
class GetChatsByID(RawMethod[ChatsResult]):
    object_guids: List[str]

    method_name = "getChatsByID"
    result = ChatsResult


@dataclass
class GetChat(GetChatsByID):
    """rubigram 0.1 name: ``getChat`` never existed; this is ``getChatsByID`` for one guid."""

    def __init__(self, object_guid: str):
        super().__init__(object_guids=[object_guid])


@dataclass
class SeenChats(RawMethod[Empty]):
    seen_list: Dict[str, str]

    method_name = "seenChats"
    result = Empty


@dataclass
class SetActionChat(RawMethod[Any]):
    object_guid: str
    action: str
    duration: Optional[int] = None

    method_name = "setActionChat"


@dataclass
class SetChatUseTime(RawMethod[Empty]):
    object_guid: str
    time: int

    method_name = "setChatUseTime"
    result = Empty


@dataclass
class DeleteUserChat(RawMethod[Any]):
    user_guid: str
    last_deleted_message_id: str = "0"

    method_name = "deleteUserChat"


@dataclass
class DeleteChatHistory(RawMethod[DeleteChatHistoryResult]):
    object_guid: str
    last_message_id: str

    method_name = "deleteChatHistory"
    result = DeleteChatHistoryResult


@dataclass
class DeleteBotChat(RawMethod[Any]):
    bot_guid: str
    last_deleted_message_id: str = "0"

    method_name = "deleteBotChat"


@dataclass
class DeleteServiceChat(RawMethod[Any]):
    service_guid: str
    last_deleted_message_id: str = "0"

    method_name = "deleteServiceChat"


@dataclass
class DeleteNoAccessGroupChat(RawMethod[Any]):
    group_guid: str

    method_name = "deleteNoAccessGroupChat"


@dataclass
class GetChatAds(RawMethod[ChatAdsResult]):
    state: Optional[int] = None

    method_name = "getChatAds"
    result = ChatAdsResult


@dataclass
class GetRelatedObjects(RawMethod[Any]):
    object_guid: str
    start_id: Optional[str] = None

    method_name = "getRelatedObjects"


@dataclass
class ClickMessageUrl(RawMethod[Empty]):
    object_guid: str
    message_id: str
    link_url: str

    method_name = "clickMessageUrl"
    result = Empty


@dataclass
class GetMessageShareUrl(RawMethod[ShareUrl]):
    object_guid: str
    message_id: str

    method_name = "getMessageShareUrl"
    result = ShareUrl


@dataclass
class GetLinkFromAppUrl(RawMethod[Any]):
    app_url: str

    method_name = "getLinkFromAppUrl"


__all__ = [
    "GetChats",
    "GetChatsUpdates",
    "GetChatsByID",
    "GetChat",
    "SeenChats",
    "SetActionChat",
    "SetChatUseTime",
    "DeleteUserChat",
    "DeleteChatHistory",
    "DeleteBotChat",
    "DeleteServiceChat",
    "DeleteNoAccessGroupChat",
    "GetChatAds",
    "GetRelatedObjects",
    "ClickMessageUrl",
    "GetMessageShareUrl",
    "GetLinkFromAppUrl",
]
