"""Stickers, GIF set and chat folders."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from rubigram.client.base import BaseClient
from rubigram.raw.functions import build_updated_parameters
from rubigram.raw.methods import (
    ActionOnStickerSet,
    AddFolder,
    AddToMyGifSet,
    DeleteFolder,
    EditFolder,
    GetFolders,
    GetMyArchivedStickerSets,
    GetMyGifSet,
    GetMyStickerSets,
    GetStickersByEmoji,
    GetStickersBySetIDs,
    GetStickerSetByID,
    GetStickerSetting,
    GetSuggestedFolders,
    GetTrendStickerSets,
    SearchStickers,
    SetPinChatInFolder,
)
from rubigram.types import Empty, FolderResult, FoldersResult, GifSet, RawObject, StickerSetResult, StickerSets, StickerSetting


class Stickers(BaseClient):
    async def get_my_sticker_sets(self) -> StickerSets:
        """Installed sticker sets (``getMyStickerSets``). [HTTP]"""
        return await self.invoke(GetMyStickerSets())

    async def get_sticker_set_by_id(self, sticker_set_id: str) -> StickerSetResult:
        """One sticker set with its stickers (``getStickerSetByID``). [HTTP]"""
        return await self.invoke(GetStickerSetByID(sticker_set_id=sticker_set_id))

    async def get_stickers_by_set_ids(self, sticker_set_ids: Sequence[str]) -> StickerSets:
        """Several sticker sets at once (``getStickersBySetIDs``). [HTTP]"""
        return await self.invoke(GetStickersBySetIDs(sticker_set_ids=list(sticker_set_ids)))

    async def get_stickers_by_emoji(self, emoji_character: str, *, suggest_by: str = "All") -> StickerSets:
        """Stickers matching an emoji (``getStickersByEmoji``). [HTTP]"""
        return await self.invoke(GetStickersByEmoji(emoji_character=emoji_character, suggest_by=suggest_by))

    async def search_stickers(self, search_text: str, start_id: Optional[str] = None) -> StickerSets:
        """Search sticker sets by text (``searchStickers``). [HTTP]"""
        return await self.invoke(SearchStickers(search_text=search_text, start_id=start_id))

    async def get_trend_sticker_sets(self, start_id: Optional[str] = None) -> StickerSets:
        """Trending sticker sets (``getTrendStickerSets``). [HTTP]"""
        return await self.invoke(GetTrendStickerSets(start_id=start_id))

    async def get_my_archived_sticker_sets(self, *, search_text: Optional[str] = None, start_id: Optional[str] = None) -> StickerSets:
        """Archived sticker sets (``getMyArchivedStickerSets``). [HTTP]"""
        return await self.invoke(GetMyArchivedStickerSets(search_text=search_text, start_id=start_id))

    async def action_on_sticker_set(self, sticker_set_id: str, action: Any) -> Empty:
        """``actionOnStickerSet`` (``Add`` / ``Remove``). [HTTP]"""
        return await self.invoke(ActionOnStickerSet(sticker_set_id=sticker_set_id, action=str(getattr(action, "value", action))))

    async def add_sticker_set(self, sticker_set_id: str) -> Empty:
        """Install a sticker set (``actionOnStickerSet`` / ``Add``). [HTTP]"""
        return await self.action_on_sticker_set(sticker_set_id, "Add")

    async def remove_sticker_set(self, sticker_set_id: str) -> Empty:
        """Uninstall a sticker set (``actionOnStickerSet`` / ``Remove``). [HTTP]"""
        return await self.action_on_sticker_set(sticker_set_id, "Remove")

    async def get_sticker_setting(self) -> StickerSetting:
        """Sticker suggestion settings (``getStickerSetting``). [HTTP]"""
        return await self.invoke(GetStickerSetting())

    async def send_sticker(self, object_guid: Any, sticker: Any, *, reply_to_message_id: Optional[str] = None) -> Any:
        """Send a sticker object (from a sticker set or a received message). [HTTP]"""
        payload = sticker.to_dict() if hasattr(sticker, "to_dict") else dict(sticker)
        return await self.send_message(object_guid, sticker=payload, reply_to_message_id=reply_to_message_id)

    async def get_my_gif_set(self) -> GifSet:
        """Saved GIFs (``getMyGifSet``). [HTTP]"""
        return await self.invoke(GetMyGifSet())

    async def add_to_my_gif_set(self, object_guid: Any, message_id: Any) -> RawObject:
        """Save a GIF message to your GIF set (``addToMyGifSet``). [HTTP]"""
        return await self.invoke(AddToMyGifSet(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id)))

    # -- folders ------------------------------------------------------------------

    async def get_folders(self, last_state: Optional[int] = None) -> FoldersResult:
        """Chat folders (``getFolders``); the state is persisted. [HTTP]"""
        if last_state is None:
            last_state = await self.storage.folders_state()
        result = await self.invoke(GetFolders(last_state=last_state))
        if result.new_state is not None:
            await self.storage.set_folders_state(result.new_state)
        return result

    async def get_suggested_folders(self) -> FoldersResult:
        """Folder suggestions (``getSuggestedFolders``). [HTTP]"""
        return await self.invoke(GetSuggestedFolders())

    async def add_folder(
        self,
        name: str,
        *,
        include_chat_types: Sequence[Any] | None = None,
        exclude_chat_types: Sequence[Any] | None = None,
        include_object_guids: Sequence[Any] | None = None,
        exclude_object_guids: Sequence[Any] | None = None,
        is_add_to_top: Optional[bool] = None,
    ) -> FolderResult:
        """Create a chat folder (``addFolder``). [HTTP]"""
        return await self.invoke(
            AddFolder(
                name=name,
                include_chat_types=self._plain_list(include_chat_types) or None,
                exclude_chat_types=self._plain_list(exclude_chat_types) or None,
                include_object_guids=self._resolve_guids(include_object_guids) or None,
                exclude_object_guids=self._resolve_guids(exclude_object_guids) or None,
                is_add_to_top=is_add_to_top,
            )
        )

    async def edit_folder(
        self,
        folder_id: str,
        *,
        name: Optional[str] = None,
        include_chat_types: Sequence[Any] | None = None,
        exclude_chat_types: Sequence[Any] | None = None,
        include_object_guids: Sequence[Any] | None = None,
        exclude_object_guids: Sequence[Any] | None = None,
    ) -> FolderResult:
        """Change a chat folder; only the given fields are sent (``editFolder``). [HTTP]"""
        values, names = build_updated_parameters(
            {
                "name": name,
                "include_chat_types": self._plain_list(include_chat_types) if include_chat_types is not None else None,
                "exclude_chat_types": self._plain_list(exclude_chat_types) if exclude_chat_types is not None else None,
                "include_object_guids": self._resolve_guids(include_object_guids) if include_object_guids is not None else None,
                "exclude_object_guids": self._resolve_guids(exclude_object_guids) if exclude_object_guids is not None else None,
            }
        )
        if not names:
            raise ValueError("At least one folder field must be provided")
        return await self.invoke(EditFolder(folder_id=folder_id, updated_parameters=names, **values))

    async def delete_folder(self, folder_id: str) -> FolderResult:
        """Delete a chat folder (``deleteFolder``). [HTTP]"""
        return await self.invoke(DeleteFolder(folder_id=folder_id))

    async def set_pin_chat_in_folder(self, folder_id: str, object_guid: Any, action: Any = "Pin") -> RawObject:
        """Pin or unpin a chat inside a folder (``setPinChatInFolder``). [HTTP]"""
        return await self.invoke(
            SetPinChatInFolder(
                folder_id=folder_id, object_guid=self._resolve_object_guid(object_guid), action=str(getattr(action, "value", action))
            )
        )


__all__ = ["Stickers"]
