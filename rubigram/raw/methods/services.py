"""Bots (user side), services, web apps, wallet, payments, Rubino, live and voice chat RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rubigram.enums import DcType
from rubigram.network.discovery import BARCODE_URL, BASE_INFO_URL, SERVICES_URL, WEBAPP_URL
from rubigram.raw.base import RawMethod
from rubigram.types import BaseInfo, Empty, ForwardedMessages, RubinoPostsResult, RubinoStoriesResult, SentMessage


# -- bots (user side) --------------------------------------------------------


@dataclass
class GetBotInfo(RawMethod[Any]):
    bot_guid: str

    method_name = "getBotInfo"


@dataclass
class StopBot(RawMethod[Any]):
    bot_guid: str

    method_name = "stopBot"


@dataclass
class GetSelection(RawMethod[Any]):
    bot_guid: str
    selection_id: str
    start_id: Optional[str] = None

    method_name = "getSelection"


@dataclass
class SearchSelection(RawMethod[Any]):
    bot_guid: str
    selection_id: str
    search_text: str
    limit: int = 20

    method_name = "searchSelection"


@dataclass
class SendMessageAPICall(RawMethod[ForwardedMessages]):
    """A bot inline-button call; goes to the bot DC pool."""

    object_guid: str
    message_id: str
    button_id: str
    text: Optional[str] = None
    rnd: Optional[str] = None
    aux_data: Optional[Dict[str, Any]] = None

    method_name = "sendMessageAPICall"
    dc_type = DcType.BOT
    result = ForwardedMessages


# -- services and web apps ---------------------------------------------------


@dataclass
class GetServiceInfo(RawMethod[Any]):
    service_guid: str

    method_name = "getServiceInfo"


@dataclass
class GetBaseInfo(RawMethod[BaseInfo]):
    method_name = "getBaseInfo"
    auth_mode = "none"
    api_version = "0"
    service_url = BASE_INFO_URL
    result = BaseInfo


@dataclass
class GetLandingPage(RawMethod[Any]):
    page_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    method_name = "getLandingPage"
    auth_mode = "none"
    api_version = "0"
    service_url = SERVICES_URL

    def to_input(self) -> Dict[str, Any]:
        payload = dict(self.data or {})
        if self.page_id is not None:
            payload.setdefault("page_id", self.page_id)
        return payload


@dataclass
class GetWebAppFunction(RawMethod[Any]):
    app_id: str

    method_name = "getWebAppFunction"
    auth_mode = "none"
    api_version = "1"
    service_url = WEBAPP_URL


@dataclass
class GetBarcodeAction(RawMethod[Any]):
    barcode: str

    method_name = "getBarcodeAction"
    auth_mode = "none"
    api_version = "0"
    service_url = BARCODE_URL


@dataclass
class GetLinkObject(RawMethod[Any]):
    share_string: str

    method_name = "getlinkObject"


@dataclass
class GetMapView(RawMethod[Any]):
    location: Dict[str, Any]

    method_name = "getMapView"


# -- wallet and payments -----------------------------------------------------


@dataclass
class GetWalletTransferMessage(RawMethod[Any]):
    object_guid: str
    message_id: str
    transfer_id: Optional[str] = None

    method_name = "getWalletTransferMessage"


@dataclass
class SendWalletTransferMessage(RawMethod[SentMessage]):
    object_guid: str
    rnd: str
    amount: Optional[int] = None
    text: Optional[str] = None
    wallet_transfer: Optional[Dict[str, Any]] = None

    method_name = "sendWalletTransferMessage"
    result = SentMessage


@dataclass
class GetPaymentInfo(RawMethod[Any]):
    payment_id: str

    method_name = "getPaymentInfo"


# -- Rubino ------------------------------------------------------------------


@dataclass
class GetProfilePosts(RawMethod[RubinoPostsResult]):
    target_profile_id: str
    max_id: Optional[str] = None
    min_id: Optional[str] = None
    equal: Optional[bool] = None
    limit: int = 1
    sort: str = "FromMax"

    method_name = "getProfilePosts"
    auth_mode = "none"
    api_version = "0"
    dc_type = DcType.RUBINO
    result = RubinoPostsResult


@dataclass
class GetProfilesStoryList(RawMethod[RubinoStoriesResult]):
    profile_story_ids: List[Dict[str, Any]]

    method_name = "getProfilesStoryList"
    auth_mode = "none"
    api_version = "0"
    dc_type = DcType.RUBINO
    result = RubinoStoriesResult


@dataclass
class SendRubinoPost(RawMethod[SentMessage]):
    object_guid: str
    rnd: str
    post_id: str
    post_profile_id: str
    text: Optional[str] = None

    method_name = "sendRubinoPost"
    result = SentMessage


# -- live --------------------------------------------------------------------


@dataclass
class SendLive(RawMethod[SentMessage]):
    object_guid: str
    rnd: str
    title: Optional[str] = None
    thumb_inline: Optional[str] = None
    live_id: Optional[str] = None
    access_token: Optional[str] = None

    method_name = "sendLive"
    result = SentMessage


@dataclass
class StopLive(RawMethod[Any]):
    live_id: str

    method_name = "stopLive"


@dataclass
class GetLiveStatus(RawMethod[Any]):
    live_id: str
    access_token: str

    method_name = "getLiveStatus"


@dataclass
class GetLivePlayUrl(RawMethod[Any]):
    live_id: str
    access_token: str

    method_name = "getLivePlayUrl"


@dataclass
class GetLiveViewers(RawMethod[Any]):
    live_id: str
    start_id: Optional[str] = None

    method_name = "getLiveViewers"


@dataclass
class GetLiveComments(RawMethod[Any]):
    live_id: str
    start_id: Optional[str] = None

    method_name = "getLiveComments"


@dataclass
class AddLiveComment(RawMethod[Any]):
    live_id: str
    text: str
    rnd: str

    method_name = "addLiveComment"


@dataclass
class SetLiveSetting(RawMethod[Any]):
    live_id: str
    updated_parameters: List[str]
    allow_comment: Optional[bool] = None

    method_name = "setLiveSetting"


# -- group voice chats -------------------------------------------------------


@dataclass
class CreateGroupVoiceChat(RawMethod[Any]):
    chat_guid: str

    method_name = "createGroupVoiceChat"


@dataclass
class DiscardGroupVoiceChat(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str

    method_name = "discardGroupVoiceChat"


@dataclass
class GetGroupVoiceChat(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str

    method_name = "getGroupVoiceChat"


@dataclass
class GetGroupVoiceChatParticipants(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str
    start_id: Optional[str] = None

    method_name = "getGroupVoiceChatParticipants"


@dataclass
class GetGroupVoiceChatParticipantsByObjectGuids(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str
    object_guids: List[str]

    method_name = "getGroupVoiceChatParticipantsByObjectGuids"


@dataclass
class GetGroupVoiceChatUpdates(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str
    state: int

    method_name = "getGroupVoiceChatUpdates"


@dataclass
class JoinGroupVoiceChat(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str
    sdp_offer_data: str
    self_object_guid: str

    method_name = "joinGroupVoiceChat"


@dataclass
class LeaveGroupVoiceChat(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str

    method_name = "leaveGroupVoiceChat"


@dataclass
class SendGroupVoiceChatActivity(RawMethod[Empty]):
    chat_guid: str
    voice_chat_id: str
    activity: str = "Speaking"
    participant_object_guid: Optional[str] = None

    method_name = "sendGroupVoiceChatActivity"
    retries = 0
    result = Empty


@dataclass
class SetGroupVoiceChatSetting(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str
    updated_parameters: List[str]
    join_muted: Optional[bool] = None
    title: Optional[str] = None

    method_name = "setGroupVoiceChatSetting"


@dataclass
class SetGroupVoiceChatState(RawMethod[Any]):
    chat_guid: str
    voice_chat_id: str
    participant_object_guid: str
    action: str

    method_name = "setGroupVoiceChatState"


@dataclass
class GetDisplayAsInGroupVoiceChat(RawMethod[Any]):
    chat_guid: str
    start_id: Optional[str] = None

    method_name = "getDisplayAsInGroupVoiceChat"


__all__ = [
    "GetBotInfo",
    "StopBot",
    "GetSelection",
    "SearchSelection",
    "SendMessageAPICall",
    "GetServiceInfo",
    "GetBaseInfo",
    "GetLandingPage",
    "GetWebAppFunction",
    "GetBarcodeAction",
    "GetLinkObject",
    "GetMapView",
    "GetWalletTransferMessage",
    "SendWalletTransferMessage",
    "GetPaymentInfo",
    "GetProfilePosts",
    "GetProfilesStoryList",
    "SendRubinoPost",
    "SendLive",
    "StopLive",
    "GetLiveStatus",
    "GetLivePlayUrl",
    "GetLiveViewers",
    "GetLiveComments",
    "AddLiveComment",
    "SetLiveSetting",
    "CreateGroupVoiceChat",
    "DiscardGroupVoiceChat",
    "GetGroupVoiceChat",
    "GetGroupVoiceChatParticipants",
    "GetGroupVoiceChatParticipantsByObjectGuids",
    "GetGroupVoiceChatUpdates",
    "JoinGroupVoiceChat",
    "LeaveGroupVoiceChat",
    "SendGroupVoiceChatActivity",
    "SetGroupVoiceChatSetting",
    "SetGroupVoiceChatState",
    "GetDisplayAsInGroupVoiceChat",
]
