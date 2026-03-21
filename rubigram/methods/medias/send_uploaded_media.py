import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

import rubigram
from rubigram import enums
from rubigram import raw
from rubigram import types
from rubigram import utils

class SendUploadedMedia:
    async def send_uploaded_media(
        self: "rubigram.Client",
        *,
        object_guid: str,
        path: str | Path,
        media_type: str,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        text: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
        extra_file_inline: Optional[Dict[str, Any]] = None,
    ) -> types.SentMessage:
        file_path = Path(path)
        file_name = file_path.name
        file_size = file_path.stat().st_size
        file_mime = mime or self.guess_upload_mime(file_path)
        descriptor = await self.request_send_file(file_name=file_name, size=file_size, mime=file_mime)
        uploaded = await self.upload_file(
            path=file_path,
            descriptor=descriptor,
            progress=progress,
            progress_args=progress_args,
        )

        file_inline: Dict[str, Any] = {
            "file_name": file_name,
            "size": file_size,
            "type": media_type,
            "dc_id": uploaded.dc_id,
            "file_id": uploaded.id,
            "mime": file_mime,
            "access_hash_rec": uploaded.access_hash_rec,
        }
        if extra_file_inline:
            file_inline.update(extra_file_inline)

        return await self.send_message(
            object_guid=object_guid,
            rnd=rnd or str(time.time_ns()),
            text=text,
            file_inline=file_inline,
        )