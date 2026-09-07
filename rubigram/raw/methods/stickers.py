"""Sticker, GIF and folder RPCs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from rubigram.raw.base import RawMethod
from rubigram.types import Empty, FolderResult, FoldersResult, GifSet, StickerSetResult, StickerSets, StickerSetting


@dataclass
class GetMyStickerSets(RawMethod[StickerSets]):
    method_name = "getMyStickerSets"
    result = StickerSets


@dataclass
class GetStickerSetByID(RawMethod[StickerSetResult]):
    sticker_set_id: str

    method_name = "getStickerSetByID"
    result = StickerSetResult


@dataclass
class GetStickersBySetIDs(RawMethod[StickerSets]):
    sticker_set_ids: List[str]

    method_name = "getStickersBySetIDs"
    result = StickerSets


@dataclass
class GetStickersByEmoji(RawMethod[StickerSets]):
    emoji_character: str
    suggest_by: str = "All"

    method_name = "getStickersByEmoji"
    result = StickerSets


@dataclass
class SearchStickers(RawMethod[StickerSets]):
    search_text: str
    start_id: Optional[str] = None

    method_name = "searchStickers"
    result = StickerSets


@dataclass
class GetTrendStickerSets(RawMethod[StickerSets]):
    start_id: Optional[str] = None

    method_name = "getTrendStickerSets"
    result = StickerSets


@dataclass
class GetMyArchivedStickerSets(RawMethod[StickerSets]):
    search_text: Optional[str] = None
    start_id: Optional[str] = None

    method_name = "getMyArchivedStickerSets"
    result = StickerSets


@dataclass
class ActionOnStickerSet(RawMethod[Empty]):
    sticker_set_id: str
    action: str = "Add"

    method_name = "actionOnStickerSet"
    result = Empty


@dataclass
class GetStickerSetting(RawMethod[StickerSetting]):
    method_name = "getStickerSetting"
    result = StickerSetting


@dataclass
class GetMyGifSet(RawMethod[GifSet]):
    method_name = "getMyGifSet"
    result = GifSet


@dataclass
class AddToMyGifSet(RawMethod[Any]):
    object_guid: str
    message_id: str

    method_name = "addToMyGifSet"


# -- folders -----------------------------------------------------------------


@dataclass
class GetFolders(RawMethod[FoldersResult]):
    last_state: Optional[int] = None

    method_name = "getFolders"
    result = FoldersResult


@dataclass
class GetSuggestedFolders(RawMethod[FoldersResult]):
    method_name = "getSuggestedFolders"
    result = FoldersResult


@dataclass
class AddFolder(RawMethod[FolderResult]):
    name: str
    include_chat_types: Optional[List[str]] = None
    exclude_chat_types: Optional[List[str]] = None
    include_object_guids: Optional[List[str]] = None
    exclude_object_guids: Optional[List[str]] = None
    is_add_to_top: Optional[bool] = None

    method_name = "addFolder"
    result = FolderResult


@dataclass
class EditFolder(RawMethod[FolderResult]):
    folder_id: str
    updated_parameters: List[str]
    name: Optional[str] = None
    include_chat_types: Optional[List[str]] = None
    exclude_chat_types: Optional[List[str]] = None
    include_object_guids: Optional[List[str]] = None
    exclude_object_guids: Optional[List[str]] = None

    method_name = "editFolder"
    result = FolderResult


@dataclass
class DeleteFolder(RawMethod[FolderResult]):
    folder_id: str

    method_name = "deleteFolder"
    result = FolderResult


@dataclass
class SetPinChatInFolder(RawMethod[Any]):
    folder_id: str
    object_guid: str
    action: str = "Pin"

    method_name = "setPinChatInFolder"


__all__ = [
    "ActionOnStickerSet",
    "AddFolder",
    "AddToMyGifSet",
    "DeleteFolder",
    "EditFolder",
    "GetFolders",
    "GetMyArchivedStickerSets",
    "GetMyGifSet",
    "GetMyStickerSets",
    "GetStickerSetByID",
    "GetStickerSetting",
    "GetStickersByEmoji",
    "GetStickersBySetIDs",
    "GetSuggestedFolders",
    "GetTrendStickerSets",
    "SearchStickers",
    "SetPinChatInFolder",
]
