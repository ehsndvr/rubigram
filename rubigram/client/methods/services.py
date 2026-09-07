"""User-side bot interaction, services, web apps, wallet, live and voice chats."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from rubigram.raw.functions import build_updated_parameters
from rubigram.raw.methods import (
    AddLiveComment,
    CreateGroupVoiceChat,
    DiscardGroupVoiceChat,
    GetBarcodeAction,
    GetBotInfo,
    GetDisplayAsInGroupVoiceChat,
    GetGroupVoiceChat,
    GetGroupVoiceChatParticipants,
    GetGroupVoiceChatParticipantsByObjectGuids,
    GetGroupVoiceChatUpdates,
    GetLandingPage,
    GetLiveComments,
    GetLivePlayUrl,
    GetLiveStatus,
    GetLiveViewers,
    GetMapView,
    GetPaymentInfo,
    GetSelection,
    GetServiceInfo,
    GetWalletTransferMessage,
    GetWebAppFunction,
    JoinGroupVoiceChat,
    LeaveGroupVoiceChat,
    SearchSelection,
    SendGroupVoiceChatActivity,
    SendLive,
    SendMessageAPICall,
    SendWalletTransferMessage,
    SetGroupVoiceChatSetting,
    SetGroupVoiceChatState,
    SetLiveSetting,
    StopBot,
    StopLive,
)
from rubigram.types import Empty, ForwardedMessages, RawObject, SentMessage

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client


class Services:
    # -- bots seen from a user account -----------------------------------------------

    async def get_bot_info(self: "Client", bot_guid: Any) -> RawObject:
        """``getBotInfo``. [HTTP]"""
        return await self.invoke(GetBotInfo(bot_guid=self._resolve_object_guid(bot_guid)))

    async def stop_bot(self: "Client", bot_guid: Any) -> RawObject:
        return await self.invoke(StopBot(bot_guid=self._resolve_object_guid(bot_guid)))

    async def get_selection(self: "Client", bot_guid: Any, selection_id: str, start_id: Optional[str] = None) -> RawObject:
        return await self.invoke(GetSelection(bot_guid=self._resolve_object_guid(bot_guid), selection_id=selection_id, start_id=start_id))

    async def search_selection(self: "Client", bot_guid: Any, selection_id: str, search_text: str, limit: int = 20) -> RawObject:
        return await self.invoke(SearchSelection(bot_guid=self._resolve_object_guid(bot_guid), selection_id=selection_id, search_text=search_text, limit=limit))

    async def click_bot_button(self: "Client", object_guid: Any, message_id: Any, button_id: str, *, text: Optional[str] = None, aux_data: Optional[Dict[str, Any]] = None) -> ForwardedMessages:
        """Press an inline button of a bot message (``sendMessageAPICall``). [HTTP]"""
        return await self.invoke(SendMessageAPICall(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id), button_id=button_id, text=text, rnd=self._new_rnd(), aux_data=aux_data))

    send_message_api_call = click_bot_button

    # -- services / web apps ---------------------------------------------------------

    async def get_service_info(self: "Client", service_guid: Any) -> RawObject:
        return await self.invoke(GetServiceInfo(service_guid=self._resolve_object_guid(service_guid)))

    async def get_landing_page(self: "Client", page_id: Optional[str] = None, **data: Any) -> RawObject:
        return await self.invoke(GetLandingPage(page_id=page_id, data=data or None))

    async def get_web_app_function(self: "Client", app_id: str) -> RawObject:
        return await self.invoke(GetWebAppFunction(app_id=app_id))

    async def get_barcode_action(self: "Client", barcode: str) -> RawObject:
        return await self.invoke(GetBarcodeAction(barcode=barcode))

    async def get_map_view(self: "Client", latitude: float, longitude: float) -> RawObject:
        return await self.invoke(GetMapView(location={"latitude": float(latitude), "longitude": float(longitude)}))

    # -- wallet and payments ------------------------------------------------------------

    async def get_wallet_transfer_message(self: "Client", object_guid: Any, message_id: Any, transfer_id: Optional[str] = None) -> RawObject:
        return await self.invoke(GetWalletTransferMessage(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id), transfer_id=transfer_id))

    async def send_wallet_transfer_message(self: "Client", object_guid: Any, *, amount: Optional[int] = None, text: Optional[str] = None, wallet_transfer: Optional[Dict[str, Any]] = None) -> SentMessage:
        return await self.invoke(SendWalletTransferMessage(object_guid=self._resolve_object_guid(object_guid), rnd=self._new_rnd(), amount=amount, text=text, wallet_transfer=wallet_transfer))

    async def get_payment_info(self: "Client", payment_id: str) -> RawObject:
        return await self.invoke(GetPaymentInfo(payment_id=payment_id))

    # -- live ---------------------------------------------------------------------------

    async def send_live(self: "Client", object_guid: Any, *, title: Optional[str] = None, thumb_inline: Optional[str] = None, live_id: Optional[str] = None, access_token: Optional[str] = None) -> SentMessage:
        return await self.invoke(SendLive(object_guid=self._resolve_object_guid(object_guid), rnd=self._new_rnd(), title=title, thumb_inline=thumb_inline, live_id=live_id, access_token=access_token))

    async def stop_live(self: "Client", live_id: str) -> RawObject:
        return await self.invoke(StopLive(live_id=live_id))

    async def get_live_status(self: "Client", live_id: str, access_token: str) -> RawObject:
        return await self.invoke(GetLiveStatus(live_id=live_id, access_token=access_token))

    async def get_live_play_url(self: "Client", live_id: str, access_token: str) -> RawObject:
        return await self.invoke(GetLivePlayUrl(live_id=live_id, access_token=access_token))

    async def get_live_viewers(self: "Client", live_id: str, start_id: Optional[str] = None) -> RawObject:
        return await self.invoke(GetLiveViewers(live_id=live_id, start_id=start_id))

    async def get_live_comments(self: "Client", live_id: str, start_id: Optional[str] = None) -> RawObject:
        return await self.invoke(GetLiveComments(live_id=live_id, start_id=start_id))

    async def add_live_comment(self: "Client", live_id: str, text: str) -> RawObject:
        return await self.invoke(AddLiveComment(live_id=live_id, text=text, rnd=self._new_rnd()))

    async def set_live_setting(self: "Client", live_id: str, *, allow_comment: Optional[bool] = None) -> RawObject:
        values, names = build_updated_parameters({"allow_comment": allow_comment})
        if not names:
            raise ValueError("At least one live setting must be provided")
        return await self.invoke(SetLiveSetting(live_id=live_id, updated_parameters=names, **values))

    # -- group voice chats -------------------------------------------------------------

    async def create_group_voice_chat(self: "Client", chat_guid: Any) -> RawObject:
        return await self.invoke(CreateGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid)))

    async def discard_group_voice_chat(self: "Client", chat_guid: Any, voice_chat_id: str) -> RawObject:
        return await self.invoke(DiscardGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id))

    async def get_group_voice_chat(self: "Client", chat_guid: Any, voice_chat_id: str) -> RawObject:
        return await self.invoke(GetGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id))

    async def get_group_voice_chat_participants(self: "Client", chat_guid: Any, voice_chat_id: str, start_id: Optional[str] = None) -> RawObject:
        return await self.invoke(GetGroupVoiceChatParticipants(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, start_id=start_id))

    async def get_group_voice_chat_participants_by_object_guids(self: "Client", chat_guid: Any, voice_chat_id: str, object_guids: Sequence[Any]) -> RawObject:
        return await self.invoke(GetGroupVoiceChatParticipantsByObjectGuids(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, object_guids=self._resolve_guids(object_guids)))

    async def get_group_voice_chat_updates(self: "Client", chat_guid: Any, voice_chat_id: str, state: int) -> RawObject:
        return await self.invoke(GetGroupVoiceChatUpdates(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, state=int(state)))

    async def join_group_voice_chat(self: "Client", chat_guid: Any, voice_chat_id: str, sdp_offer_data: str, self_object_guid: Optional[str] = None) -> RawObject:
        return await self.invoke(JoinGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, sdp_offer_data=sdp_offer_data, self_object_guid=self_object_guid or (await self.storage.user_guid()) or ""))

    async def leave_group_voice_chat(self: "Client", chat_guid: Any, voice_chat_id: str) -> RawObject:
        return await self.invoke(LeaveGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id))

    async def send_group_voice_chat_activity(self: "Client", chat_guid: Any, voice_chat_id: str, *, activity: str = "Speaking", participant_object_guid: Optional[str] = None) -> Empty:
        return await self.invoke(SendGroupVoiceChatActivity(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, activity=activity, participant_object_guid=participant_object_guid))

    async def set_group_voice_chat_setting(self: "Client", chat_guid: Any, voice_chat_id: str, *, join_muted: Optional[bool] = None, title: Optional[str] = None) -> RawObject:
        values, names = build_updated_parameters({"join_muted": join_muted, "title": title})
        if not names:
            raise ValueError("At least one voice chat setting must be provided")
        return await self.invoke(SetGroupVoiceChatSetting(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, updated_parameters=names, **values))

    async def set_group_voice_chat_state(self: "Client", chat_guid: Any, voice_chat_id: str, participant_object_guid: Any, action: str) -> RawObject:
        return await self.invoke(SetGroupVoiceChatState(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, participant_object_guid=self._resolve_object_guid(participant_object_guid), action=action))

    async def get_display_as_in_group_voice_chat(self: "Client", chat_guid: Any, start_id: Optional[str] = None) -> RawObject:
        return await self.invoke(GetDisplayAsInGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), start_id=start_id))


__all__ = ["Services"]
