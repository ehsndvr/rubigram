from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import RawObject, SentMessage

if TYPE_CHECKING:
    import rubigram


@dataclass
class SendMessage(RawMethod[SentMessage]):
    """
    Send a text message to a chat or user.

    Requires authentication.
    """
    object_guid: str
    rnd: str
    text: str
    parse_mode: Optional[str] = None
    reply_to_message_id: Optional[str] = None

    method_name = "sendMessage"

    def to_input(self) -> Dict[str, Any]:
        input_dict = {
            "object_guid": self.object_guid,
            "rnd": self.rnd,
            "text": self.text,
        }
        if self.parse_mode:
            input_dict["parse_mode"] = self.parse_mode
        if self.reply_to_message_id:
            input_dict["reply_to_message_id"] = self.reply_to_message_id
        return input_dict

    def parse_response(self, client: "rubigram.Client", data: Any) -> SentMessage:
        return SentMessage._parse(client, data)


@dataclass
class EditMessage(RawMethod[RawObject]):
    """
    Edit an existing message.

    Requires authentication.
    """
    object_guid: str
    message_id: str
    text: str

    method_name = "editMessage"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
            "message_id": self.message_id,
            "text": self.text,
        }


@dataclass
class DeleteMessage(RawMethod[RawObject]):
    """
    Delete a message.

    Requires authentication.
    """
    object_guid: str
    message_id: str

    method_name = "deleteMessage"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
            "message_id": self.message_id,
        }


@dataclass
class GetMessages(RawMethod[RawObject]):
    """
    Get a list of messages from a chat.

    Requires authentication.
    """
    object_guid: str
    offset: int = 0
    limit: int = 20

    method_name = "getMessages"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
            "offset": self.offset,
            "limit": self.limit,
        }


@dataclass
class GetHistory(RawMethod[RawObject]):
    """
    Get the full history of a chat.

    Requires authentication.
    """
    object_guid: str
    offset: int = 0
    limit: int = 50

    method_name = "getHistory"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
            "offset": self.offset,
            "limit": self.limit,
        }


@dataclass
class GetChat(RawMethod[RawObject]):
    """
    Get information about a chat.

    Requires authentication.
    """
    object_guid: str

    method_name = "getChat"

    def to_input(self) -> Dict[str, Any]:
        return {
            "object_guid": self.object_guid,
        }
