"""File-related models: inline files, avatars, upload descriptors, URL files, stickers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .object import Object, model


async def _download_bound_file(
    target: Any,
    *,
    path: Any,
    in_memory: bool,
    file_name: Optional[str],
    progress: Any,
    progress_args: tuple[Any, ...],
    missing_message: str,
) -> Any:
    if target._client is None:
        raise RuntimeError(missing_message)
    return await target._client.download_file(
        target, path=path, in_memory=in_memory, file_name=file_name, progress=progress, progress_args=progress_args
    )


async def _download_bound_url(
    target: Any,
    *,
    path: Any,
    in_memory: bool,
    file_name: Optional[str],
    progress: Any,
    progress_args: tuple[Any, ...],
    missing_message: str,
) -> Any:
    if target._client is None:
        raise RuntimeError(missing_message)
    return await target._client.download_url(
        target.url,
        path=path,
        in_memory=in_memory,
        file_name=file_name or getattr(target, "file_name", None),
        progress=progress,
        progress_args=progress_args,
    )


@model
class DownloadableFile(Object):
    """Any server file addressed by ``file_id`` + ``dc_id`` + ``access_hash_rec``."""

    file_id: Optional[str] = None
    mime: Optional[str] = None
    dc_id: Optional[str] = None
    access_hash_rec: Optional[str] = None
    file_name: Optional[str] = None
    size: Optional[int] = None

    @property
    def is_downloadable(self) -> bool:
        return bool(self.file_id and self.dc_id and self.access_hash_rec)

    async def download(
        self,
        path: Any = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        """Download this file through the bound client (``bytes`` when ``in_memory``)."""
        return await _download_bound_file(
            self,
            path=path,
            in_memory=in_memory,
            file_name=file_name,
            progress=progress,
            progress_args=progress_args,
            missing_message="This file is not bound to a Client instance",
        )


@model
class FileInline(DownloadableFile):
    type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    time: Optional[float] = None
    thumb_inline: Optional[str] = None
    is_round: Optional[bool] = None
    is_spoil: Optional[bool] = None
    cdn_tag: Optional[str] = None
    music_performer: Optional[str] = None
    auto_play: Optional[bool] = None


@model
class StickerFile(DownloadableFile):
    cdn_tag: Optional[str] = None


@model
class AvatarThumbnail(DownloadableFile):
    async def download(
        self,
        path: Any = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        return await _download_bound_file(
            self,
            path=path,
            in_memory=in_memory,
            file_name=file_name,
            progress=progress,
            progress_args=progress_args,
            missing_message="This avatar is not bound to a Client instance",
        )


@model
class AvatarFile(DownloadableFile):
    pass


@model
class Avatar(Object):
    avatar_id: Optional[str] = None
    thumbnail: Optional[AvatarFile] = None
    main: Optional[AvatarFile] = None
    create_time: Optional[int] = None

    def _select_download_file(self, *, use_thumbnail: bool = False) -> AvatarFile:
        file = self.thumbnail if use_thumbnail else self.main
        if file is None:
            file = self.main or self.thumbnail
        if file is None:
            raise RuntimeError("This avatar does not contain downloadable file metadata")
        return file

    def _default_download_name(self, *, use_thumbnail: bool = False, index: Optional[int] = None) -> str:
        target = self._select_download_file(use_thumbnail=use_thumbnail)
        role = "thumbnail" if use_thumbnail else "main"
        extension = (target.mime or "bin").lstrip(".")
        base = self.avatar_id or f"avatar_{index or 0}"
        return f"{base}_{role}.{extension}"

    async def download(
        self,
        path: Any = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
        use_thumbnail: bool = False,
    ) -> Any:
        """Download the main (or thumbnail) image of this avatar."""
        file = self._select_download_file(use_thumbnail=use_thumbnail)
        if file._client is None:
            file.bind(self._client)
        return await file.download(
            path=path,
            in_memory=in_memory,
            file_name=file_name or self._default_download_name(use_thumbnail=use_thumbnail),
            progress=progress,
            progress_args=progress_args,
        )


@model
class ChatAvatars(Object):
    avatars: list[Avatar] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        if self.avatars is None:
            self.avatars = []

    def __iter__(self):
        return iter(self.avatars)

    def __len__(self) -> int:
        return len(self.avatars)

    def __getitem__(self, index: int) -> Avatar:
        return self.avatars[index]

    async def download(
        self,
        path: Any = None,
        *,
        in_memory: bool = False,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
        use_thumbnail: bool = False,
    ) -> list[Any]:
        """Download every avatar, naming files ``<avatar_id>_<role>.<ext>``."""
        results = []
        for index, avatar in enumerate(self.avatars, start=1):
            results.append(
                await avatar.download(
                    path=path,
                    in_memory=in_memory,
                    file_name=avatar._default_download_name(use_thumbnail=use_thumbnail, index=index),
                    progress=progress,
                    progress_args=progress_args,
                    use_thumbnail=use_thumbnail,
                )
            )
        return results


@model
class UploadDescriptor(Object):
    """Result of ``requestSendFile`` (and of a completed upload)."""

    id: Optional[str] = None
    dc_id: Optional[str] = None
    access_hash_send: Optional[str] = None
    access_hash_rec: Optional[str] = None
    upload_url: Optional[str] = None


@model
class UrlFile(Object):
    """A file addressed by a public URL (Rubino media, CDN)."""

    url: Optional[str] = None
    file_name: Optional[str] = None

    @classmethod
    def from_url(cls, client: Any, url: Optional[str], *, file_name: Optional[str] = None) -> Optional[UrlFile]:
        if not url:
            return None
        return cls(client=client, url=url, file_name=file_name or Path(str(url).rstrip("/")).name or None)

    async def download(
        self,
        path: Any = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        return await _download_bound_url(
            self,
            path=path,
            in_memory=in_memory,
            file_name=file_name,
            progress=progress,
            progress_args=progress_args,
            missing_message="This URL file is not bound to a Client instance",
        )


@model
class Sticker(Object):
    """A sticker attached to a message."""

    sticker_id: Optional[str] = None
    sticker_set_id: Optional[str] = None
    emoji_character: Optional[str] = None
    w_h_ratio: Optional[float] = None
    file: Optional[StickerFile] = None

    async def download(
        self,
        path: Any = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        if self.file is None:
            raise RuntimeError("This sticker does not contain a downloadable file")
        if self.file._client is None:
            self.file.bind(self._client)
        return await self.file.download(path=path, in_memory=in_memory, file_name=file_name, progress=progress, progress_args=progress_args)


__all__ = [
    "Avatar",
    "AvatarFile",
    "AvatarThumbnail",
    "ChatAvatars",
    "DownloadableFile",
    "FileInline",
    "Sticker",
    "StickerFile",
    "UploadDescriptor",
    "UrlFile",
]
