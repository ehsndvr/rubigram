"""Uploads, downloads, media messages, avatars and wallpapers."""

from __future__ import annotations

import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from rubigram.errors import LoginRequired, TransportError
from rubigram.raw.functions import build_file_inline, guess_upload_mime
from rubigram.raw.methods import AddSetWallpaper, DeleteAvatar, GetWallpapers, RequestSendFile, ResetWallpapers, UploadAvatar
from rubigram.types import Empty, RawObject, SentMessage, UploadDescriptor
from rubigram.utils import parse_ogg_opus_duration_ms

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client

ProgressCallback = Any


class Media:
    # -- upload ----------------------------------------------------------------

    async def request_send_file(self: "Client", file_name: Optional[str] = None, size: Optional[int] = None, mime: Optional[str] = None, *, type: Any = None) -> Any:
        """``requestSendFile``: an upload slot (``upload_url``, ``id``, ``dc_id``, ``access_hash_send``). [HTTP][bot]"""
        if self.is_bot:
            if type is None:
                raise ValueError("Bot request_send_file() requires type")
            return await self._bot_request_send_file(str(getattr(type, "value", type)))
        if not file_name or size is None:
            raise ValueError("request_send_file() requires file_name and size")
        return await self.invoke(RequestSendFile(file_name=file_name, size=int(size), mime=mime or guess_upload_mime(file_name)))

    async def upload_file(
        self: "Client",
        path: Union[str, Path, None] = None,
        *,
        data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        mime: Optional[str] = None,
        descriptor: Optional[UploadDescriptor] = None,
        upload_url: Optional[str] = None,
        progress: Optional[ProgressCallback] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        """Upload a file and return its :class:`~rubigram.types.UploadDescriptor` (bots: the ``file_id``). [HTTP][bot]"""
        if self.is_bot:
            if upload_url is None or path is None:
                raise ValueError("Bot upload_file() requires upload_url and path")
            return await self.upload_bot_file(upload_url, path)
        if self._upload is None:
            raise TransportError("Upload transport is not initialized")
        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("Uploading files requires an authenticated session")
        if data is None and path is None:
            raise ValueError("upload_file() needs a path or data")
        if descriptor is None:
            name = file_name or (Path(path).name if path is not None else f"file_{int(time.time())}")
            size = len(data) if data is not None else Path(path).stat().st_size  # type: ignore[arg-type]
            descriptor = await self.request_send_file(name, size, mime or guess_upload_mime(name))
        return await self._upload.upload_file(auth=auth, descriptor=descriptor, path=path, data=data, progress=progress, progress_args=progress_args)

    async def _upload_file(self: "Client", *, path: Union[str, Path], descriptor: UploadDescriptor, progress: Any = None, progress_args: tuple[Any, ...] = ()) -> UploadDescriptor:
        return await self.upload_file(path, descriptor=descriptor, progress=progress, progress_args=progress_args)

    # -- download --------------------------------------------------------------

    async def download_file(
        self: "Client",
        file: Any,
        path: Union[str, Path, None] = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Optional[ProgressCallback] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Union[bytes, Path]:
        """Download a message/file/avatar object; returns the path or the bytes. [HTTP][bot]

        Accepts anything carrying ``file_id``/``dc_id``/``access_hash_rec``, a
        :class:`~rubigram.types.Message` (its ``file_inline`` or sticker) or a
        Bot API file with ``download_url``.
        """
        if self.is_bot or isinstance(file, str) or getattr(file, "download_url", None):
            return await self.download_bot_file(file, path=path, in_memory=in_memory, file_name=file_name)
        target = self._resolve_download_target(file)
        if self._download is None:
            raise TransportError("Download transport is not initialized")
        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("Downloading files requires an authenticated session")
        dc_id = getattr(target, "dc_id", None)
        url = self.dc.storage_url(dc_id) if dc_id is not None else None
        name = file_name or getattr(target, "file_name", None) or f"file_{getattr(target, 'file_id', 'unknown')}"
        destination = None if in_memory else self._resolve_download_destination(path, name)
        size = getattr(target, "size", None)
        try:
            file_size = int(size) if size is not None else None
        except (TypeError, ValueError):
            file_size = None
        return await self._download.download_file(
            auth=auth,
            file_id=getattr(target, "file_id"),
            access_hash_rec=getattr(target, "access_hash_rec"),
            url=url,
            dc_id=dc_id,
            file_size=file_size,
            path=destination,
            in_memory=in_memory,
            progress=progress,
            progress_args=progress_args,
        )

    async def download_url(self: "Client", url: str, path: Union[str, Path, None] = None, *, in_memory: bool = False, file_name: Optional[str] = None, progress: Optional[ProgressCallback] = None, progress_args: tuple[Any, ...] = ()) -> Union[bytes, Path]:
        """Download a public URL (Rubino media, CDN) to disk or memory. [HTTP]"""
        if self._download is None:
            self._download = self._make_download_transport()
        destination = None if in_memory else self._resolve_download_destination(path, file_name or self._default_file_name_from_url(url))
        return await self._download.download_url(url=url, path=destination, in_memory=in_memory, progress=progress, progress_args=progress_args)

    def _make_download_transport(self: "Client") -> Any:
        from rubigram.network import DownloadTransport

        return DownloadTransport(timeout=max(self.timeout, 30.0), proxy=self.proxy, retry_policy=self.retry_policy, user_agent=self.user_agent)

    @staticmethod
    def _resolve_download_target(file: Any) -> Any:
        if getattr(file, "download_url", None):
            return file
        if hasattr(file, "file_id") and hasattr(file, "dc_id") and hasattr(file, "access_hash_rec") and getattr(file, "file_id", None):
            return file
        file_inline = getattr(file, "file_inline", None)
        if file_inline is not None:
            return file_inline
        sticker = getattr(file, "sticker", None)
        if sticker is not None and getattr(sticker, "file", None) is not None:
            return sticker.file
        main = getattr(file, "main", None) or getattr(file, "thumbnail", None)
        if main is not None and getattr(main, "file_id", None):
            return main
        bot_file = getattr(file, "file", None)
        if bot_file is not None and getattr(bot_file, "file_id", None) and not getattr(bot_file, "dc_id", None):
            return bot_file
        raise ValueError("The provided object does not contain downloadable file metadata")

    @staticmethod
    def _resolve_download_destination(path: Union[str, Path, None], file_name: str) -> Path:
        if path is None:
            return Path(file_name)
        destination = Path(path)
        if destination.exists() and destination.is_dir():
            return destination / file_name
        if str(path).endswith(("/", "\\")):
            return destination / file_name
        if destination.suffix:
            return destination
        return destination / file_name

    @staticmethod
    def _default_file_name_from_url(url: str) -> str:
        candidate = Path((url or "").split("?")[0].rstrip("/")).name
        return candidate or f"file_{int(time.time())}"

    # -- media messages ------------------------------------------------------------

    async def send_media(
        self: "Client",
        object_guid: Any = None,
        path: Union[str, Path, None] = None,
        *,
        media_type: str = "File",
        text: Optional[str] = None,
        data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        mime: Optional[str] = None,
        rnd: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        parse_mode: Any = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration_ms: Optional[float] = None,
        thumb_inline: Optional[str] = None,
        is_round: Optional[bool] = None,
        is_spoil: Optional[bool] = None,
        music_performer: Optional[str] = None,
        extra_file_inline: Optional[Dict[str, Any]] = None,
        progress: Optional[ProgressCallback] = None,
        progress_args: tuple[Any, ...] = (),
        peer: Any = None,
    ) -> Any:
        """Upload ``path`` (or ``data``) and send it as ``media_type`` (``File``/``Image``/``Video``/``Voice``/``Music``/``Gif``). [HTTP][bot]"""
        guid = self._resolve_object_guid(object_guid, peer=peer)
        if self.is_bot:
            if path is None:
                raise ValueError("Bot send_media() requires a file path")
            return await self._bot_send_media(guid, path, file_type=media_type, text=text, reply_to_message_id=reply_to_message_id)
        if data is None and path is None:
            raise ValueError("send_media() needs a path or data")
        name = file_name or (Path(path).name if path is not None else f"file_{int(time.time())}")
        size = len(data) if data is not None else Path(path).stat().st_size  # type: ignore[arg-type]
        file_mime = mime or guess_upload_mime(name)
        descriptor = await self.request_send_file(name, size, file_mime)
        uploaded = await self.upload_file(path, data=data, descriptor=descriptor, progress=progress, progress_args=progress_args)
        file_inline = build_file_inline(
            file_id=uploaded.id,
            dc_id=uploaded.dc_id,
            access_hash_rec=uploaded.access_hash_rec,
            file_name=name,
            size=size,
            media_type=media_type,
            mime=file_mime,
            width=width,
            height=height,
            duration_ms=duration_ms,
            thumb_inline=thumb_inline,
            is_round=is_round,
            is_spoil=is_spoil,
            music_performer=music_performer,
            extra=extra_file_inline,
        )
        return await self.send_message(guid, text, rnd=rnd, file_inline=file_inline, reply_to_message_id=reply_to_message_id, parse_mode=parse_mode)

    async def send_uploaded_media(self: "Client", *, object_guid: Any = None, path: Union[str, Path], media_type: str, **kwargs: Any) -> SentMessage:
        """rubigram 0.1 name of :meth:`send_media`."""
        warnings.warn("send_uploaded_media() is deprecated; use send_media()", DeprecationWarning, stacklevel=2)
        return await self.send_media(object_guid, path, media_type=media_type, **kwargs)

    async def send_photo(self: "Client", object_guid: Any = None, path: Union[str, Path, None] = None, *, text: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None, is_spoil: Optional[bool] = None, **kwargs: Any) -> Any:
        """Send an image. [HTTP][bot]"""
        return await self.send_media(object_guid, path, media_type="Image", text=text, width=width, height=height, is_spoil=is_spoil, **kwargs)

    async def send_video(self: "Client", object_guid: Any = None, path: Union[str, Path, None] = None, *, text: Optional[str] = None, duration_ms: Optional[float] = None, width: Optional[int] = None, height: Optional[int] = None, is_round: bool = False, is_spoil: bool = False, thumb_inline: Optional[str] = None, **kwargs: Any) -> Any:
        """Send a video (``duration_ms``/``width``/``height`` are what the apps display). [HTTP][bot]"""
        return await self.send_media(object_guid, path, media_type="Video", text=text, duration_ms=duration_ms, width=width, height=height, is_round=is_round, is_spoil=is_spoil, thumb_inline=thumb_inline, **kwargs)

    async def send_gif(self: "Client", object_guid: Any = None, path: Union[str, Path, None] = None, *, text: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None, duration_ms: Optional[float] = None, **kwargs: Any) -> Any:
        return await self.send_media(object_guid, path, media_type="Gif", text=text, width=width, height=height, duration_ms=duration_ms, **kwargs)

    async def send_voice(self: "Client", object_guid: Any = None, path: Union[str, Path, None] = None, *, duration_ms: Optional[float] = None, text: Optional[str] = None, **kwargs: Any) -> Any:
        """Send a voice note; the duration is read from OGG/Opus files when omitted. [HTTP][bot]"""
        if not self.is_bot and path is not None:
            duration_ms = self._resolve_voice_duration_ms(Path(path), duration_ms)
        return await self.send_media(object_guid, path, media_type="Voice", text=text, duration_ms=duration_ms, **kwargs)

    async def send_music(self: "Client", object_guid: Any = None, path: Union[str, Path, None] = None, *, duration_ms: Optional[float] = None, music_performer: Optional[str] = None, text: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.send_media(object_guid, path, media_type="Music", text=text, duration_ms=duration_ms, music_performer=music_performer, **kwargs)

    async def send_document(self: "Client", object_guid: Any = None, path: Union[str, Path, None] = None, *, text: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.send_media(object_guid, path, media_type="File", text=text, **kwargs)

    send_file_message = send_document

    @staticmethod
    def _resolve_voice_duration_ms(path: Path, duration_ms: Optional[float]) -> float:
        try:
            if duration_ms is not None and float(duration_ms) > 0:
                return float(duration_ms)
        except (TypeError, ValueError):
            pass
        if path.suffix.lower() in {".ogg", ".opus", ".oga"}:
            parsed = parse_ogg_opus_duration_ms(path)
            if parsed > 0:
                return parsed
        raise ValueError("Voice duration could not be determined from the file. Pass duration_ms explicitly.")

    # -- avatars and wallpapers ------------------------------------------------------

    async def upload_avatar(self: "Client", object_guid: Any, path: Union[str, Path], *, thumbnail_path: Union[str, Path, None] = None, progress: Optional[ProgressCallback] = None, progress_args: tuple[Any, ...] = ()) -> RawObject:
        """Set the avatar of a user (own guid), group or channel (``uploadAvatar``). [HTTP]"""
        main = await self.upload_file(path, progress=progress, progress_args=progress_args)
        thumb = await self.upload_file(thumbnail_path) if thumbnail_path else main
        return await self.invoke(UploadAvatar(object_guid=self._resolve_object_guid(object_guid), thumbnail_file_id=str(thumb.id), main_file_id=str(main.id)))

    async def set_profile_photo(self: "Client", path: Union[str, Path], **kwargs: Any) -> RawObject:
        user_guid = await self.storage.user_guid()
        if not user_guid:
            raise LoginRequired("set_profile_photo requires an authenticated session")
        return await self.upload_avatar(user_guid, path, **kwargs)

    async def set_group_photo(self: "Client", object_guid: Any = None, path: Union[str, Path] = "", *, peer: Any = None, **kwargs: Any) -> RawObject:
        return await self.upload_avatar(peer if peer is not None else object_guid, path, **kwargs)

    set_channel_photo = set_group_photo

    async def upload_group_avatar(self: "Client", object_guid: Any = None, path: Union[str, Path] = "", *, peer: Any = None, **kwargs: Any) -> RawObject:
        """rubigram 0.1 name of :meth:`set_group_photo`."""
        warnings.warn("upload_group_avatar() is deprecated; use set_group_photo()", DeprecationWarning, stacklevel=2)
        return await self.set_group_photo(object_guid, path, peer=peer, **kwargs)

    async def delete_avatar(self: "Client", object_guid: Any, avatar_id: str) -> RawObject:
        return await self.invoke(DeleteAvatar(object_guid=self._resolve_object_guid(object_guid), avatar_id=avatar_id))

    async def get_wallpapers(self: "Client") -> RawObject:
        return await self.invoke(GetWallpapers())

    async def add_set_wallpaper(self: "Client", thumbnail_file_id: str, main_file_id: str) -> RawObject:
        return await self.invoke(AddSetWallpaper(thumbnail_file_id=thumbnail_file_id, main_file_id=main_file_id))

    async def reset_wallpapers(self: "Client") -> Empty:
        return await self.invoke(ResetWallpapers())


__all__ = ["Media"]
