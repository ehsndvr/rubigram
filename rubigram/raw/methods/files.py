"""File, avatar and wallpaper RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import Empty, UploadDescriptor


@dataclass
class RequestSendFile(RawMethod[UploadDescriptor]):
    file_name: str
    size: int
    mime: str

    method_name = "requestSendFile"
    result = UploadDescriptor


@dataclass
class UploadAvatar(RawMethod[Any]):
    """Set the avatar of the current user, a group or a channel (``object_guid``)."""

    object_guid: str
    thumbnail_file_id: str
    main_file_id: str

    method_name = "uploadAvatar"


@dataclass
class UploadNewGroupAvatar(UploadAvatar):
    """rubigram 0.1 name: the server method is ``uploadAvatar``; both ids default to ``file_id``."""

    def __init__(
        self,
        group_guid: str,
        file_id: str,
        dc_id: Optional[str] = None,
        access_hash_rec: Optional[str] = None,
        *,
        thumbnail_file_id: Optional[str] = None,
    ):
        super().__init__(object_guid=group_guid, thumbnail_file_id=thumbnail_file_id or file_id, main_file_id=file_id)


@dataclass
class DeleteAvatar(RawMethod[Any]):
    object_guid: str
    avatar_id: str

    method_name = "deleteAvatar"


@dataclass
class GetWallpapers(RawMethod[Any]):
    method_name = "getWallpapers"


@dataclass
class AddSetWallpaper(RawMethod[Any]):
    thumbnail_file_id: str
    main_file_id: str

    method_name = "addSetWallpaper"


@dataclass
class ResetWallpapers(RawMethod[Empty]):
    method_name = "resetWallpapers"
    result = Empty


__all__ = ["AddSetWallpaper", "DeleteAvatar", "GetWallpapers", "RequestSendFile", "ResetWallpapers", "UploadAvatar", "UploadNewGroupAvatar"]
