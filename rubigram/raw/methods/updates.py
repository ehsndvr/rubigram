from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from rubigram.raw.base import RawMethod
from rubigram.types import AvailableReactions, ChatsUpdates, ContactsUpdates

if TYPE_CHECKING:
    import rubigram


@dataclass
class GetChatsUpdates(RawMethod[ChatsUpdates]):
    state: int

    method_name = "getChatsUpdates"

    def to_input(self) -> Dict[str, Any]:
        return {
            "state": self.state,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> ChatsUpdates:
        return ChatsUpdates._parse(client, data)


@dataclass
class GetAvailableReactions(RawMethod[AvailableReactions]):
    method_name = "getAvailableReactions"

    def to_input(self) -> Dict[str, Any]:
        return {}

    def parse_response(self, client: "rubigram.Client", data: Any) -> AvailableReactions:
        return AvailableReactions._parse(client, data)


@dataclass
class GetContactsUpdates(RawMethod[ContactsUpdates]):
    state: int

    method_name = "getContactsUpdates"

    def to_input(self) -> Dict[str, Any]:
        return {
            "state": self.state,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> ContactsUpdates:
        return ContactsUpdates._parse(client, data)
