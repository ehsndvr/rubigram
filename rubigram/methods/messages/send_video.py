from pathlib import Path
from typing import Any, Callable, Optional

import rubigram
from rubigram import types


class SendVideo:
    async def send_video(
        self: "rubigram.Client",
        object_guid: str | Any = None,
        path: str | Path = "",
        *,
        peer: Any = None,
        duration_ms: float | int,
        width: int,
        height: int,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        text: Optional[str] = None,
        is_round: bool = False,
        is_spoil: bool = False,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> types.SentMessage:
        return await self._send_uploaded_media(
            object_guid=self._resolve_object_guid(object_guid, peer=peer),
            path=path,
            rnd=rnd,
            mime=mime,
            media_type="Video",
            text=text,
            progress=progress,
            progress_args=progress_args,
            extra_file_inline={
                "time": duration_ms,
                "width": width,
                "height": height,
                "is_round": is_round,
                "is_spoil": is_spoil,
            },
        )
