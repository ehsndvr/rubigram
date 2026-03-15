from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from rubigram.raw.base import RawMethod
from rubigram.types import UploadDescriptor

if TYPE_CHECKING:
    import rubigram


@dataclass
class RequestSendFile(RawMethod[UploadDescriptor]):
    file_name: str
    size: int
    mime: str

    method_name = "requestSendFile"

    def to_input(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "size": self.size,
            "mime": self.mime,
        }

    def parse_response(self, client: "rubigram.Client", data: Any) -> UploadDescriptor:
        return UploadDescriptor._parse(client, data)
