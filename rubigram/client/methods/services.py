"""User-side bot interaction, services, web apps, wallet, live and voice chats."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from rubigram.client.base import BaseClient
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


class Services(BaseClient):
    # -- bots seen from a user account -----------------------------------------------

    async def get_bot_info(self, bot_guid: Any) -> RawObject:
        """``getBotInfo``. [HTTP]"""
        return await self.invoke(GetBotInfo(bot_guid=self._resolve_object_guid(bot_guid)))

    async def stop_bot(self, bot_guid: Any) -> RawObject:
        """Stop (block) a bot (``stopBot``). [HTTP]"""
        return await self.invoke(StopBot(bot_guid=self._resolve_object_guid(bot_guid)))

    async def get_selection(self, bot_guid: Any, selection_id: str, start_id: Optional[str] = None) -> RawObject:
        """Items of a bot selection keypad (``getSelection``). [HTTP]"""
        return await self.invoke(GetSelection(bot_guid=self._resolve_object_guid(bot_guid), selection_id=selection_id, start_id=start_id))

    async def search_selection(self, bot_guid: Any, selection_id: str, search_text: str, limit: int = 20) -> RawObject:
        """Search inside a bot selection keypad (``searchSelection``). [HTTP]"""
        return await self.invoke(
            SearchSelection(bot_guid=self._resolve_object_guid(bot_guid), selection_id=selection_id, search_text=search_text, limit=limit)
        )

    async def click_bot_button(
        self, object_guid: Any, message_id: Any, button_id: str, *, text: Optional[str] = None, aux_data: Optional[Dict[str, Any]] = None
    ) -> ForwardedMessages:
        """Press an inline button of a bot message (``sendMessageAPICall``). [HTTP]"""
        return await self.invoke(
            SendMessageAPICall(
                object_guid=self._resolve_object_guid(object_guid),
                message_id=str(message_id),
                button_id=button_id,
                text=text,
                rnd=self._new_rnd(),
                aux_data=aux_data,
            )
        )

    send_message_api_call = click_bot_button

    # -- services / web apps ---------------------------------------------------------

    async def get_service_info(self, service_guid: Any) -> RawObject:
        """Information about a Rubika service (``getServiceInfo``). [HTTP]"""
        return await self.invoke(GetServiceInfo(service_guid=self._resolve_object_guid(service_guid)))

    async def get_landing_page(self, page_id: Optional[str] = None, **data: Any) -> RawObject:
        """A services landing page (``getLandingPage`` on the services base). [HTTP]"""
        return await self.invoke(GetLandingPage(page_id=page_id, data=data or None))

    async def get_web_app_function(self, app_id: str) -> RawObject:
        """Web-app function metadata (``getWebAppFunction`` on the web-app base). [HTTP]"""
        return await self.invoke(GetWebAppFunction(app_id=app_id))

    async def get_barcode_action(self, barcode: str) -> RawObject:
        """What a scanned Rubika QR code does (``getBarcodeAction``). [HTTP]"""
        return await self.invoke(GetBarcodeAction(barcode=barcode))

    async def get_map_view(self, latitude: float, longitude: float) -> RawObject:
        """Map tile information for a location (``getMapView``). [HTTP]"""
        return await self.invoke(GetMapView(location={"latitude": float(latitude), "longitude": float(longitude)}))

    # -- wallet and payments ------------------------------------------------------------

    async def get_wallet_transfer_message(self, object_guid: Any, message_id: Any, transfer_id: Optional[str] = None) -> RawObject:
        """Details of a wallet transfer message (``getWalletTransferMessage``). [HTTP]"""
        return await self.invoke(
            GetWalletTransferMessage(
                object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id), transfer_id=transfer_id
            )
        )

    async def send_wallet_transfer_message(
        self,
        object_guid: Any,
        *,
        amount: Optional[int] = None,
        text: Optional[str] = None,
        wallet_transfer: Optional[Dict[str, Any]] = None,
    ) -> SentMessage:
        """Send money through the wallet (``sendWalletTransferMessage``). [HTTP]"""
        return await self.invoke(
            SendWalletTransferMessage(
                object_guid=self._resolve_object_guid(object_guid),
                rnd=self._new_rnd(),
                amount=amount,
                text=text,
                wallet_transfer=wallet_transfer,
            )
        )

    async def get_payment_info(self, payment_id: str) -> RawObject:
        """Details of a payment (``getPaymentInfo``). [HTTP]"""
        return await self.invoke(GetPaymentInfo(payment_id=payment_id))

    # -- live ---------------------------------------------------------------------------

    async def send_live(
        self,
        object_guid: Any,
        *,
        title: Optional[str] = None,
        thumb_inline: Optional[str] = None,
        live_id: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> SentMessage:
        """Start a live stream message (``sendLive``). [HTTP]"""
        return await self.invoke(
            SendLive(
                object_guid=self._resolve_object_guid(object_guid),
                rnd=self._new_rnd(),
                title=title,
                thumb_inline=thumb_inline,
                live_id=live_id,
                access_token=access_token,
            )
        )

    async def stop_live(self, live_id: str) -> RawObject:
        """End a live stream (``stopLive``). [HTTP]"""
        return await self.invoke(StopLive(live_id=live_id))

    async def get_live_status(self, live_id: str, access_token: str) -> RawObject:
        """Status of a live stream (``getLiveStatus``). [HTTP]"""
        return await self.invoke(GetLiveStatus(live_id=live_id, access_token=access_token))

    async def get_live_play_url(self, live_id: str, access_token: str) -> RawObject:
        """Playback URL of a live stream (``getLivePlayUrl``). [HTTP]"""
        return await self.invoke(GetLivePlayUrl(live_id=live_id, access_token=access_token))

    async def get_live_viewers(self, live_id: str, start_id: Optional[str] = None) -> RawObject:
        """Viewers of a live stream (``getLiveViewers``). [HTTP]"""
        return await self.invoke(GetLiveViewers(live_id=live_id, start_id=start_id))

    async def get_live_comments(self, live_id: str, start_id: Optional[str] = None) -> RawObject:
        """Comments of a live stream (``getLiveComments``). [HTTP]"""
        return await self.invoke(GetLiveComments(live_id=live_id, start_id=start_id))

    async def add_live_comment(self, live_id: str, text: str) -> RawObject:
        """Post a comment on a live stream (``addLiveComment``). [HTTP]"""
        return await self.invoke(AddLiveComment(live_id=live_id, text=text, rnd=self._new_rnd()))

    async def set_live_setting(self, live_id: str, *, allow_comment: Optional[bool] = None) -> RawObject:
        """Change live stream settings such as ``allow_comment`` (``setLiveSetting``). [HTTP]"""
        values, names = build_updated_parameters({"allow_comment": allow_comment})
        if not names:
            raise ValueError("At least one live setting must be provided")
        return await self.invoke(SetLiveSetting(live_id=live_id, updated_parameters=names, **values))

    # -- group voice chats -------------------------------------------------------------

    async def create_group_voice_chat(self, chat_guid: Any) -> RawObject:
        """Start a voice chat in a group or channel (``createGroupVoiceChat``). [HTTP]"""
        return await self.invoke(CreateGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid)))

    async def discard_group_voice_chat(self, chat_guid: Any, voice_chat_id: str) -> RawObject:
        """End a voice chat (``discardGroupVoiceChat``). [HTTP]"""
        return await self.invoke(DiscardGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id))

    async def get_group_voice_chat(self, chat_guid: Any, voice_chat_id: str) -> RawObject:
        """State of a voice chat (``getGroupVoiceChat``). [HTTP]"""
        return await self.invoke(GetGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id))

    async def get_group_voice_chat_participants(self, chat_guid: Any, voice_chat_id: str, start_id: Optional[str] = None) -> RawObject:
        """Participants of a voice chat, one page at a time (``getGroupVoiceChatParticipants``). [HTTP]"""
        return await self.invoke(
            GetGroupVoiceChatParticipants(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, start_id=start_id)
        )

    async def get_group_voice_chat_participants_by_object_guids(
        self, chat_guid: Any, voice_chat_id: str, object_guids: Sequence[Any]
    ) -> RawObject:
        """Voice chat state of specific participants (``getGroupVoiceChatParticipantsByObjectGuids``). [HTTP]"""
        return await self.invoke(
            GetGroupVoiceChatParticipantsByObjectGuids(
                chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, object_guids=self._resolve_guids(object_guids)
            )
        )

    async def get_group_voice_chat_updates(self, chat_guid: Any, voice_chat_id: str, state: int) -> RawObject:
        """Changes in a voice chat since ``state`` (``getGroupVoiceChatUpdates``). [HTTP]"""
        return await self.invoke(
            GetGroupVoiceChatUpdates(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, state=int(state))
        )

    async def join_group_voice_chat(
        self, chat_guid: Any, voice_chat_id: str, sdp_offer_data: str, self_object_guid: Optional[str] = None
    ) -> RawObject:
        """Join a voice chat with a WebRTC SDP offer (``joinGroupVoiceChat``). [HTTP]"""
        return await self.invoke(
            JoinGroupVoiceChat(
                chat_guid=self._resolve_object_guid(chat_guid),
                voice_chat_id=voice_chat_id,
                sdp_offer_data=sdp_offer_data,
                self_object_guid=self_object_guid or (await self.storage.user_guid()) or "",
            )
        )

    async def leave_group_voice_chat(self, chat_guid: Any, voice_chat_id: str) -> RawObject:
        """Leave a voice chat (``leaveGroupVoiceChat``). [HTTP]"""
        return await self.invoke(LeaveGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id))

    async def send_group_voice_chat_activity(
        self, chat_guid: Any, voice_chat_id: str, *, activity: str = "Speaking", participant_object_guid: Optional[str] = None
    ) -> Empty:
        """Report speaking activity in a voice chat (``sendGroupVoiceChatActivity``). [HTTP]"""
        return await self.invoke(
            SendGroupVoiceChatActivity(
                chat_guid=self._resolve_object_guid(chat_guid),
                voice_chat_id=voice_chat_id,
                activity=activity,
                participant_object_guid=participant_object_guid,
            )
        )

    async def set_group_voice_chat_setting(
        self, chat_guid: Any, voice_chat_id: str, *, join_muted: Optional[bool] = None, title: Optional[str] = None
    ) -> RawObject:
        """Change the title or join-muted flag of a voice chat (``setGroupVoiceChatSetting``). [HTTP]"""
        values, names = build_updated_parameters({"join_muted": join_muted, "title": title})
        if not names:
            raise ValueError("At least one voice chat setting must be provided")
        return await self.invoke(
            SetGroupVoiceChatSetting(
                chat_guid=self._resolve_object_guid(chat_guid), voice_chat_id=voice_chat_id, updated_parameters=names, **values
            )
        )

    async def set_group_voice_chat_state(self, chat_guid: Any, voice_chat_id: str, participant_object_guid: Any, action: str) -> RawObject:
        """Mute or unmute a participant (``setGroupVoiceChatState``). [HTTP]"""
        return await self.invoke(
            SetGroupVoiceChatState(
                chat_guid=self._resolve_object_guid(chat_guid),
                voice_chat_id=voice_chat_id,
                participant_object_guid=self._resolve_object_guid(participant_object_guid),
                action=action,
            )
        )

    async def get_display_as_in_group_voice_chat(self, chat_guid: Any, start_id: Optional[str] = None) -> RawObject:
        """Identities you can join a voice chat as (``getDisplayAsInGroupVoiceChat``). [HTTP]"""
        return await self.invoke(GetDisplayAsInGroupVoiceChat(chat_guid=self._resolve_object_guid(chat_guid), start_id=start_id))


__all__ = ["Services"]
