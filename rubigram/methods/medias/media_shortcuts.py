from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

import rubigram
from rubigram.bot.enums import FileType as BotFileType
from rubigram.types import SentMessage


class MediaShortcuts:
    async def send_voice(
        self: "rubigram.Client",
        object_guid: Any = None,
        path: str | Path = "",
        *,
        peer: Any = None,
        rnd: Optional[str] = None,
        duration_ms: float | int = 0,
        mime: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> SentMessage:
        if self.is_bot:
            return await self.send_media(self._resolve_object_guid(object_guid, peer=peer), path, type=BotFileType.VOICE)

        file_path = Path(path)
        resolved_duration_ms = self._resolve_voice_duration_ms(file_path, duration_ms)
        return await self._send_uploaded_media(
            object_guid=self._resolve_object_guid(object_guid, peer=peer),
            path=file_path,
            rnd=rnd,
            mime=mime,
            media_type="Voice",
            progress=progress,
            progress_args=progress_args,
            extra_file_inline={"time": resolved_duration_ms},
        )

    async def send_music(
        self: "rubigram.Client",
        object_guid: Any = None,
        path: str | Path = "",
        *,
        peer: Any = None,
        duration_ms: float | int = 0,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> SentMessage:
        if self.is_bot:
            return await self.send_media(self._resolve_object_guid(object_guid, peer=peer), path, type=BotFileType.MUSIC)

        return await self._send_uploaded_media(
            object_guid=self._resolve_object_guid(object_guid, peer=peer),
            path=path,
            rnd=rnd,
            mime=mime,
            media_type="Music",
            progress=progress,
            progress_args=progress_args,
            extra_file_inline={"time": duration_ms},
        )

    async def send_photo(
        self: "rubigram.Client",
        object_guid: Any = None,
        path: str | Path = "",
        *,
        peer: Any = None,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        text: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> SentMessage:
        if self.is_bot:
            return await self.send_media(self._resolve_object_guid(object_guid, peer=peer), path, type=BotFileType.IMAGE, text=text)

        extra_file_inline: dict[str, Any] = {}
        if width is not None:
            extra_file_inline["width"] = width
        if height is not None:
            extra_file_inline["height"] = height

        return await self._send_uploaded_media(
            object_guid=self._resolve_object_guid(object_guid, peer=peer),
            path=path,
            rnd=rnd,
            mime=mime,
            media_type="Image",
            text=text,
            progress=progress,
            progress_args=progress_args,
            extra_file_inline=extra_file_inline or None,
        )

    async def send_document(
        self: "rubigram.Client",
        object_guid: Any = None,
        path: str | Path = "",
        *,
        peer: Any = None,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        text: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> SentMessage:
        if self.is_bot:
            return await self.send_media(self._resolve_object_guid(object_guid, peer=peer), path, type=BotFileType.FILE, text=text)

        return await self._send_uploaded_media(
            object_guid=self._resolve_object_guid(object_guid, peer=peer),
            path=path,
            rnd=rnd,
            mime=mime,
            media_type="File",
            text=text,
            progress=progress,
            progress_args=progress_args,
        )
