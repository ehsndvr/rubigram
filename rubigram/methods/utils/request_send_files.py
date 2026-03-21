import mimetypes
from pathlib import Path

import rubigram
from rubigram.types.results import UploadDescriptor
from rubigram.raw.methods import RequestSendFile


class RequestSendFiles:
    async def request_send_file(
            self: "rubigram.Client",
            file_name: str,
            size: int, mime: str
    ) -> UploadDescriptor:
        return await self.invoke(RequestSendFile(file_name=file_name, size=size, mime=mime))
