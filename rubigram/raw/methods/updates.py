from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from rubigram.raw.base import RawMethod
from rubigram.types import ChatsUpdates

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
