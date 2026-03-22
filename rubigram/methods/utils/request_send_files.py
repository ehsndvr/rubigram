import rubigram
from rubigram.types.results import UploadDescriptor
from rubigram.raw.methods import RequestSendFile
from rubigram.bot.enums import FileType as BotFileType


class RequestSendFiles:
    async def request_send_file(
        self: "rubigram.Client",
        file_name: str | None = None,
        size: int | None = None,
        mime: str | None = None,
        *,
        type: str | BotFileType | None = None,
    ) -> UploadDescriptor | dict:
        if self.is_bot:
            if type is None:
                raise ValueError("Bot request_send_file() requires type")
            return await self._invoke_bot("requestSendFile", {"type": str(type)})
        return await self.invoke(RequestSendFile(file_name=file_name, size=size, mime=mime))
