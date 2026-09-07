"""Message RPCs: send, edit, delete, forward, fetch, search, pin, reactions, polls, drafts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import (
    AvailableReactions,
    ChatReactions,
    DeletedMessages,
    Empty,
    ForwardedMessages,
    MessageReactions,
    MessageReadParticipants,
    MessageReadParticipants as _ReadParticipants,
    MessageReactions as _Reactions,
    MessagesResult,
    MessagesUpdates,
    PollOptionVoters,
    PollStatusResult,
    SearchMessagesResult,
    SentMessage,
)


@dataclass
class SendMessage(RawMethod[SentMessage]):
    object_guid: str
    rnd: str
    text: Optional[str] = None
    file_inline: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    reply_to_message_id: Optional[str] = None
    sticker: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    aux_data: Optional[Dict[str, Any]] = None
    is_mute: Optional[bool] = None
    parse_mode: Optional[str] = None  # legacy field; never sent (metadata is built client-side)

    method_name = "sendMessage"
    result = SentMessage

    def to_input(self) -> Dict[str, Any]:
        data = super().to_input()
        data.pop("parse_mode", None)
        return data


@dataclass
class EditMessage(RawMethod[SentMessage]):
    object_guid: str
    message_id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None

    method_name = "editMessage"
    result = SentMessage


@dataclass
class DeleteMessages(RawMethod[DeletedMessages]):
    object_guid: str
    message_ids: List[str]
    type: str = "Global"

    method_name = "deleteMessages"
    result = DeletedMessages


@dataclass
class DeleteMessage(DeleteMessages):
    """rubigram 0.1 name: ``deleteMessage`` never existed; this deletes one message via ``deleteMessages``."""

    def __init__(self, object_guid: str, message_id: str, type: str = "Global"):
        super().__init__(object_guid=object_guid, message_ids=[message_id], type=type)


@dataclass
class ForwardMessages(RawMethod[ForwardedMessages]):
    from_object_guid: str
    to_object_guid: str
    message_ids: List[str]
    rnd: str

    method_name = "forwardMessages"
    result = ForwardedMessages


@dataclass
class GetMessages(RawMethod[MessagesResult]):
    """Paginated history: ``max_id`` with ``FromMax`` walks backwards, ``min_id`` with ``FromMin`` forwards."""

    object_guid: str
    max_id: Optional[str] = None
    min_id: Optional[str] = None
    sort: str = "FromMax"
    limit: int = 20
    filter_type: Optional[str] = None

    method_name = "getMessages"
    result = MessagesResult


@dataclass
class GetHistory(GetMessages):
    """rubigram 0.1 name: ``getHistory`` never existed; alias of :class:`GetMessages`."""


@dataclass
class GetMessagesByID(RawMethod[MessagesResult]):
    object_guid: str
    message_ids: List[str]

    method_name = "getMessagesByID"
    result = MessagesResult


@dataclass
class GetMessagesInterval(RawMethod[MessagesResult]):
    object_guid: str
    middle_message_id: str
    filter_type: Optional[str] = None

    method_name = "getMessagesInterval"
    result = MessagesResult


@dataclass
class GetMessagesUpdates(RawMethod[MessagesUpdates]):
    object_guid: str
    state: int

    method_name = "getMessagesUpdates"
    result = MessagesUpdates


@dataclass
class SetPinMessage(RawMethod[SentMessage]):
    object_guid: str
    message_id: str
    action: str = "Pin"

    method_name = "setPinMessage"
    result = SentMessage


@dataclass
class SearchChatMessages(RawMethod[SearchMessagesResult]):
    object_guid: str
    search_text: str
    type: str = "Text"

    method_name = "searchChatMessages"
    result = SearchMessagesResult


@dataclass
class SearchGlobalMessages(RawMethod[SearchMessagesResult]):
    search_text: str
    type: str = "Text"
    start_id: Optional[str] = None

    method_name = "searchGlobalMessages"
    result = SearchMessagesResult


@dataclass
class SendChatActivity(RawMethod[Empty]):
    object_guid: str
    activity: str = "Typing"

    method_name = "sendChatActivity"
    retries = 0
    result = Empty


@dataclass
class GetGroupMessageReadParticipants(RawMethod[MessageReadParticipants]):
    group_guid: str
    message_id: str

    method_name = "getGroupMessageReadParticipants"
    result = _ReadParticipants


@dataclass
class TranscribeVoice(RawMethod[Any]):
    object_guid: str
    message_id: str

    method_name = "transcribeVoice"


@dataclass
class GetTranscription(RawMethod[Any]):
    message_id: str
    transcription_id: str

    method_name = "getTranscription"


# -- reactions ---------------------------------------------------------------


@dataclass
class GetAvailableReactions(RawMethod[AvailableReactions]):
    method_name = "getAvailableReactions"
    result = AvailableReactions


@dataclass
class ActionOnMessageReaction(RawMethod[MessageReactions]):
    object_guid: str
    message_id: str
    reaction_id: int
    action: str = "Add"

    method_name = "actionOnMessageReaction"
    result = _Reactions


@dataclass
class GetMessageReactions(RawMethod[MessageReactions]):
    object_guid: str
    message_id: str
    reaction_id: Optional[int] = None
    start_id: Optional[str] = None

    method_name = "getMessageReactions"
    result = _Reactions


@dataclass
class GetChatReaction(RawMethod[ChatReactions]):
    object_guid: str

    method_name = "getChatReaction"
    result = ChatReactions


# -- polls -------------------------------------------------------------------


@dataclass
class CreatePoll(RawMethod[SentMessage]):
    object_guid: str
    question: str
    options: List[str]
    rnd: str
    type: str = "Regular"
    is_anonymous: bool = True
    allows_multiple_answers: bool = False
    correct_option_index: Optional[int] = None
    explanation: Optional[str] = None

    method_name = "createPoll"
    result = SentMessage


@dataclass
class VotePoll(RawMethod[PollStatusResult]):
    poll_id: str
    selection_index: int

    method_name = "votePoll"
    result = PollStatusResult


@dataclass
class GetPollStatus(RawMethod[PollStatusResult]):
    poll_id: str

    method_name = "getPollStatus"
    result = PollStatusResult


@dataclass
class GetPollOptionVoters(RawMethod[PollOptionVoters]):
    poll_id: str
    selection_index: int
    start_id: Optional[str] = None

    method_name = "getPollOptionVoters"
    result = PollOptionVoters


# -- drafts ------------------------------------------------------------------


@dataclass
class GetAllDrafts(RawMethod[Any]):
    method_name = "getAllDrafts"


@dataclass
class ClearDrafts(RawMethod[Any]):
    action: str = "All"
    object_guid: Optional[str] = None

    method_name = "clearDrafts"


__all__ = [
    "SendMessage",
    "EditMessage",
    "DeleteMessages",
    "DeleteMessage",
    "ForwardMessages",
    "GetMessages",
    "GetHistory",
    "GetMessagesByID",
    "GetMessagesInterval",
    "GetMessagesUpdates",
    "SetPinMessage",
    "SearchChatMessages",
    "SearchGlobalMessages",
    "SendChatActivity",
    "GetGroupMessageReadParticipants",
    "TranscribeVoice",
    "GetTranscription",
    "GetAvailableReactions",
    "ActionOnMessageReaction",
    "GetMessageReactions",
    "GetChatReaction",
    "CreatePoll",
    "VotePoll",
    "GetPollStatus",
    "GetPollOptionVoters",
    "GetAllDrafts",
    "ClearDrafts",
]
