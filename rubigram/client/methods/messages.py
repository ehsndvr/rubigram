"""Sending, editing, fetching and searching messages; reactions, polls, drafts."""

from __future__ import annotations

import warnings
from typing import Any, AsyncIterator, Dict, Optional, Sequence

from rubigram.client.base import BaseClient
from rubigram.raw.functions import build_message_metadata
from rubigram.raw.methods import (
    ActionOnMessageReaction,
    ClearDrafts,
    CreatePoll,
    DeleteMessages,
    EditMessage,
    ForwardMessages,
    GetAllDrafts,
    GetAvailableReactions,
    GetChatReaction,
    GetGroupMessageReadParticipants,
    GetMessageReactions,
    GetMessages,
    GetMessagesByID,
    GetMessagesInterval,
    GetPollOptionVoters,
    GetPollStatus,
    GetTranscription,
    SearchChatMessages,
    SearchGlobalMessages,
    SendChatActivity,
    SendMessage,
    SetPinMessage,
    TranscribeVoice,
    VotePoll,
)
from rubigram.types import (
    AvailableReactions,
    ChatReactions,
    DeletedMessages,
    Empty,
    ForwardedMessages,
    Message,
    MessageEntity,
    MessageReactions,
    MessageReadParticipants,
    MessagesResult,
    PollOptionVoters,
    PollStatusResult,
    RawObject,
    SearchMessagesResult,
    SentMessage,
)


def _bind_chat(result: MessagesResult, object_guid: str) -> MessagesResult:
    """The server omits ``object_guid`` inside history messages; add it so bound helpers work."""
    for message in result.messages or []:
        if not message.object_guid:
            message.object_guid = object_guid
    return result


class Messages(BaseClient):
    async def send_message(
        self,
        object_guid: Any = None,
        text: Optional[str] = None,
        rnd: Optional[str] = None,
        *,
        parse_mode: Any = None,
        entities: Optional[Sequence[MessageEntity]] = None,
        reply_to_message_id: Optional[str] = None,
        file_inline: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sticker: Optional[Dict[str, Any]] = None,
        location: Optional[Dict[str, Any]] = None,
        aux_data: Optional[Dict[str, Any]] = None,
        is_mute: Optional[bool] = None,
        peer: Any = None,
        chat_keypad: Any = None,
        inline_keypad: Any = None,
        chat_keypad_type: Any = None,
        disable_notification: bool = False,
    ) -> Any:
        """Send a text (or an already uploaded ``file_inline``) message. [HTTP][bot]

        ``parse_mode`` (``"markdown"`` / ``"html"``) or explicit ``entities``
        become Rubika ``metadata``.  For bots the Bot API keypad arguments apply
        and the result is a :class:`rubigram.types.bot.SentMessage`.
        """
        if rnd is not None and text is not None and str(text).isdigit() and not str(rnd).isdigit():
            warnings.warn(
                "send_message(object_guid, rnd, text) is deprecated; pass text second and rnd as a keyword",
                DeprecationWarning,
                stacklevel=2,
            )
            text, rnd = rnd, text
        guid = self._resolve_object_guid(object_guid, peer=peer)
        if self.is_bot:
            if text is None:
                raise ValueError("Bot send_message() requires text")
            return await self._bot_send_message(
                chat_id=guid,
                text=text,
                chat_keypad=chat_keypad,
                inline_keypad=inline_keypad,
                chat_keypad_type=chat_keypad_type,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
            )
        plain_text, built_metadata = build_message_metadata(text, entities=entities, parse_mode=parse_mode)
        return await self.invoke(
            SendMessage(
                object_guid=guid,
                rnd=str(rnd) if rnd is not None else self._new_rnd(),
                text=plain_text,
                file_inline=file_inline,
                metadata=metadata or built_metadata,
                reply_to_message_id=str(reply_to_message_id) if reply_to_message_id else None,
                sticker=sticker,
                location=location,
                aux_data=aux_data,
                is_mute=is_mute,
            )
        )

    async def send_location(
        self, object_guid: Any, latitude: Any, longitude: Any, *, reply_to_message_id: Optional[str] = None, **bot_kwargs: Any
    ) -> Any:
        """Send a location. [HTTP][bot]"""
        if self.is_bot:
            return await self._bot_send_location(
                self._resolve_object_guid(object_guid), str(latitude), str(longitude), reply_to_message_id=reply_to_message_id, **bot_kwargs
            )
        return await self.send_message(
            object_guid, location={"latitude": float(latitude), "longitude": float(longitude)}, reply_to_message_id=reply_to_message_id
        )

    async def edit_message(
        self,
        object_guid: Any = None,
        message_id: Any = "",
        text: str = "",
        *,
        parse_mode: Any = None,
        entities: Optional[Sequence[MessageEntity]] = None,
        peer: Any = None,
    ) -> Any:
        """Edit the text of a message (``editMessage``). [HTTP][bot]"""
        guid = self._resolve_object_guid(object_guid, peer=peer)
        if self.is_bot:
            return await self._bot_edit_message_text(guid, str(message_id), text)
        plain_text, metadata = build_message_metadata(text, entities=entities, parse_mode=parse_mode)
        return await self.invoke(EditMessage(object_guid=guid, message_id=str(message_id), text=plain_text or "", metadata=metadata))

    async def delete_messages(
        self, object_guid: Any, message_ids: Sequence[Any], *, delete_type: Any = "Global", peer: Any = None
    ) -> DeletedMessages:
        """Delete messages for everyone (``Global``) or locally (``Local``) (``deleteMessages``). [HTTP]"""
        self._require_user_session("delete_messages")
        return await self.invoke(
            DeleteMessages(
                object_guid=self._resolve_object_guid(object_guid, peer=peer),
                message_ids=[str(item) for item in message_ids],
                type=str(getattr(delete_type, "value", delete_type)),
            )
        )

    async def delete_message(self, object_guid: Any = None, message_id: Any = "", *, delete_type: Any = "Global", peer: Any = None) -> Any:
        """Delete one message (``deleteMessages``; Bot API ``deleteMessage`` for bots). [HTTP][bot]"""
        guid = self._resolve_object_guid(object_guid, peer=peer)
        if self.is_bot:
            return await self._bot_delete_message(guid, str(message_id))
        return await self.delete_messages(guid, [message_id], delete_type=delete_type)

    async def forward_messages(self, from_object_guid: Any, to_object_guid: Any, message_ids: Sequence[Any]) -> ForwardedMessages:
        """``forwardMessages``. [HTTP]"""
        self._require_user_session("forward_messages")
        return await self.invoke(
            ForwardMessages(
                from_object_guid=self._resolve_object_guid(from_object_guid),
                to_object_guid=self._resolve_object_guid(to_object_guid),
                message_ids=[str(item) for item in message_ids],
                rnd=self._new_rnd(),
            )
        )

    async def forward_message(
        self, from_object_guid: Any, message_id: Any, to_object_guid: Any, *, disable_notification: bool = False
    ) -> Any:
        """Forward one message (user sessions and bots). [HTTP][bot]"""
        if self.is_bot:
            return await self._bot_forward_message(
                self._resolve_object_guid(from_object_guid),
                str(message_id),
                self._resolve_object_guid(to_object_guid),
                disable_notification=disable_notification,
            )
        return await self.forward_messages(from_object_guid, to_object_guid, [message_id])

    async def get_messages(
        self,
        object_guid: Any = None,
        *,
        max_id: Optional[Any] = None,
        min_id: Optional[Any] = None,
        sort: Any = "FromMax",
        limit: int = 20,
        filter_type: Optional[Any] = None,
        peer: Any = None,
    ) -> MessagesResult:
        """A page of history (``getMessages``): ``max_id`` + ``FromMax`` goes backwards. [HTTP]"""
        guid = self._resolve_object_guid(object_guid, peer=peer)
        result = await self.invoke(
            GetMessages(
                object_guid=guid,
                max_id=str(max_id) if max_id is not None else None,
                min_id=str(min_id) if min_id is not None else None,
                sort=str(getattr(sort, "value", sort)),
                limit=int(limit),
                filter_type=str(getattr(filter_type, "value", filter_type)) if filter_type is not None else None,
            )
        )
        return _bind_chat(result, guid)

    async def get_history(self, object_guid: Any = None, offset: Any = None, limit: int = 50, *, peer: Any = None) -> MessagesResult:
        """rubigram 0.1 name of :meth:`get_messages` (``offset`` is treated as ``max_id``)."""
        warnings.warn("get_history() is deprecated; use get_messages()", DeprecationWarning, stacklevel=2)
        return await self.get_messages(object_guid, max_id=offset or None, limit=limit, peer=peer)

    async def iter_messages(
        self, object_guid: Any, *, limit: Optional[int] = None, filter_type: Optional[Any] = None, page_size: int = 20
    ) -> AsyncIterator[Message]:
        """Walk a chat history from the newest message backwards. [HTTP]"""
        max_id: Optional[str] = None
        seen = 0
        while True:
            page = await self.get_messages(object_guid, max_id=max_id, limit=page_size, filter_type=filter_type)
            if not page.messages:
                return
            for message in sorted(page.messages, key=lambda m: int(m.message_id or 0), reverse=True):
                yield message
                seen += 1
                if limit is not None and seen >= limit:
                    return
            if not page.has_continue:
                return
            oldest = min(int(m.message_id or 0) for m in page.messages)
            max_id = str(oldest - 1)

    async def get_messages_by_id(self, object_guid: Any, message_ids: Sequence[Any]) -> MessagesResult:
        """``getMessagesByID``. [HTTP]"""
        guid = self._resolve_object_guid(object_guid)
        return _bind_chat(await self.invoke(GetMessagesByID(object_guid=guid, message_ids=[str(item) for item in message_ids])), guid)

    async def get_message(self, object_guid: Any, message_id: Any) -> Optional[Message]:
        """One message by id, or ``None``. [HTTP]"""
        result = await self.get_messages_by_id(object_guid, [message_id])
        return result.messages[0] if result.messages else None

    async def get_messages_interval(self, object_guid: Any, middle_message_id: Any, *, filter_type: Optional[Any] = None) -> MessagesResult:
        """Messages around ``middle_message_id`` (``getMessagesInterval``). [HTTP]"""
        guid = self._resolve_object_guid(object_guid)
        return _bind_chat(
            await self.invoke(
                GetMessagesInterval(
                    object_guid=guid,
                    middle_message_id=str(middle_message_id),
                    filter_type=str(getattr(filter_type, "value", filter_type)) if filter_type is not None else None,
                )
            ),
            guid,
        )

    async def pin_message(self, object_guid: Any, message_id: Any) -> SentMessage:
        """``setPinMessage`` / ``Pin``. [HTTP]"""
        return await self.invoke(
            SetPinMessage(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id), action="Pin")
        )

    async def unpin_message(self, object_guid: Any, message_id: Any) -> SentMessage:
        """``setPinMessage`` / ``Unpin``. [HTTP]"""
        return await self.invoke(
            SetPinMessage(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id), action="Unpin")
        )

    async def search_chat_messages(self, object_guid: Any, search_text: str, *, search_type: Any = "Text") -> SearchMessagesResult:
        """``searchChatMessages`` (returns message ids). [HTTP]"""
        return await self.invoke(
            SearchChatMessages(
                object_guid=self._resolve_object_guid(object_guid),
                search_text=search_text,
                type=str(getattr(search_type, "value", search_type)),
            )
        )

    async def search_global_messages(
        self, search_text: str, *, search_type: Any = "Text", start_id: Optional[str] = None
    ) -> SearchMessagesResult:
        """``searchGlobalMessages``. [HTTP]"""
        return await self.invoke(
            SearchGlobalMessages(search_text=search_text, type=str(getattr(search_type, "value", search_type)), start_id=start_id)
        )

    async def send_chat_activity(self, object_guid: Any = None, activity: Any = "Typing", *, peer: Any = None) -> Empty:
        """``sendChatActivity`` (``Typing`` / ``Recording`` / ``Uploading``); never retried. [HTTP]"""
        self._require_user_session("send_chat_activity")
        return await self.invoke(
            SendChatActivity(
                object_guid=self._resolve_object_guid(object_guid, peer=peer), activity=str(getattr(activity, "value", activity))
            )
        )

    async def send_typing(self, object_guid: Any = None, *, peer: Any = None) -> Empty:
        """Show the *typing…* activity in a chat (``sendChatActivity`` / ``Typing``). [HTTP]"""
        return await self.send_chat_activity(object_guid, "Typing", peer=peer)

    async def get_message_read_participants(self, group_guid: Any, message_id: Any) -> MessageReadParticipants:
        """Who read a group message (``getGroupMessageReadParticipants``). [HTTP]"""
        return await self.invoke(
            GetGroupMessageReadParticipants(group_guid=self._resolve_object_guid(group_guid), message_id=str(message_id))
        )

    async def transcribe_voice(self, object_guid: Any, message_id: Any) -> RawObject:
        """Ask the server to transcribe a voice message (``transcribeVoice``). [HTTP]"""
        return await self.invoke(TranscribeVoice(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id)))

    async def get_transcription(self, message_id: Any, transcription_id: str) -> RawObject:
        """Fetch a voice transcription started with :meth:`transcribe_voice` (``getTranscription``). [HTTP]"""
        return await self.invoke(GetTranscription(message_id=str(message_id), transcription_id=transcription_id))

    # -- reactions ------------------------------------------------------------

    async def get_available_reactions(self) -> AvailableReactions:
        """``getAvailableReactions``. [HTTP]"""
        return await self.invoke(GetAvailableReactions())

    async def action_on_message_reaction(
        self, object_guid: Any, message_id: Any, reaction_id: Any, action: Any = "Add"
    ) -> MessageReactions:
        """``actionOnMessageReaction`` (``Add`` / ``Remove``). [HTTP]"""
        return await self.invoke(
            ActionOnMessageReaction(
                object_guid=self._resolve_object_guid(object_guid),
                message_id=str(message_id),
                reaction_id=int(reaction_id),
                action=str(getattr(action, "value", action)),
            )
        )

    async def react(self, object_guid: Any, message_id: Any, reaction_id: Any) -> MessageReactions:
        """Add a reaction (see :meth:`get_available_reactions` for ids). [HTTP]"""
        return await self.action_on_message_reaction(object_guid, message_id, reaction_id, "Add")

    async def unreact(self, object_guid: Any, message_id: Any, reaction_id: Any) -> MessageReactions:
        """Remove your reaction from a message (``actionOnMessageReaction`` / ``Remove``). [HTTP]"""
        return await self.action_on_message_reaction(object_guid, message_id, reaction_id, "Remove")

    async def get_message_reactions(
        self, object_guid: Any, message_id: Any, *, reaction_id: Optional[Any] = None, start_id: Optional[str] = None
    ) -> MessageReactions:
        """Who reacted to a message, optionally for one ``reaction_id`` (``getMessageReactions``). [HTTP]"""
        return await self.invoke(
            GetMessageReactions(
                object_guid=self._resolve_object_guid(object_guid),
                message_id=str(message_id),
                reaction_id=int(reaction_id) if reaction_id is not None else None,
                start_id=start_id,
            )
        )

    async def get_chat_reaction(self, object_guid: Any) -> ChatReactions:
        """Reactions allowed in a chat (``getChatReaction``). [HTTP]"""
        return await self.invoke(GetChatReaction(object_guid=self._resolve_object_guid(object_guid)))

    # -- polls ------------------------------------------------------------------

    async def create_poll(
        self,
        object_guid: Any,
        question: str,
        options: Sequence[str],
        *,
        poll_type: Any = "Regular",
        is_anonymous: bool = True,
        allows_multiple_answers: bool = False,
        correct_option_index: Optional[int] = None,
        explanation: Optional[str] = None,
    ) -> Any:
        """Create a poll or quiz (``createPoll``; Bot API ``sendPoll`` for bots). [HTTP][bot]"""
        guid = self._resolve_object_guid(object_guid)
        if self.is_bot:
            return await self._bot_send_poll(guid, question, list(options))
        return await self.invoke(
            CreatePoll(
                object_guid=guid,
                question=question,
                options=list(options),
                rnd=self._new_rnd(),
                type=str(getattr(poll_type, "value", poll_type)),
                is_anonymous=is_anonymous,
                allows_multiple_answers=allows_multiple_answers,
                correct_option_index=correct_option_index,
                explanation=explanation,
            )
        )

    async def send_poll(self, object_guid: Any, question: str, options: Sequence[str], **kwargs: Any) -> Any:
        """Alias of :meth:`create_poll` (Bot API name). [HTTP][bot]"""
        return await self.create_poll(object_guid, question, options, **kwargs)

    async def vote_poll(self, poll_id: str, selection_index: int) -> PollStatusResult:
        """Vote for ``selection_index`` in a poll (``votePoll``). [HTTP]"""
        return await self.invoke(VotePoll(poll_id=poll_id, selection_index=int(selection_index)))

    async def get_poll_status(self, poll_id: str) -> PollStatusResult:
        """Current votes of a poll (``getPollStatus``). [HTTP]"""
        return await self.invoke(GetPollStatus(poll_id=poll_id))

    async def get_poll_option_voters(self, poll_id: str, selection_index: int, start_id: Optional[str] = None) -> PollOptionVoters:
        """Voters of one poll option (``getPollOptionVoters``). [HTTP]"""
        return await self.invoke(GetPollOptionVoters(poll_id=poll_id, selection_index=int(selection_index), start_id=start_id))

    # -- drafts -----------------------------------------------------------------

    async def get_all_drafts(self) -> RawObject:
        """Every unsent draft (``getAllDrafts``). [HTTP]"""
        return await self.invoke(GetAllDrafts())

    async def clear_drafts(self, object_guid: Any = None) -> RawObject:
        """Clear one chat's draft or every draft (``clearDrafts``). [HTTP]"""
        if object_guid is None:
            return await self.invoke(ClearDrafts(action="All"))
        return await self.invoke(ClearDrafts(action="Chat", object_guid=self._resolve_object_guid(object_guid)))


__all__ = ["Messages"]
