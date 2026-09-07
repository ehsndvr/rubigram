"""Stickers, GIF set and chat folders."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Sequence

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
    GetStickerSetByID,
    GetStickersByEmoji,
    GetStickersBySetIDs,
    GetStickerSetting,
    GetSuggestedFolders,
    GetTrendStickerSets,
    SearchStickers,
    SetPinChatInFolder,
)
from rubigram.types import Empty, FolderResult, FoldersResult, GifSet, RawObject, StickerSetResult, StickerSets, StickerSetting

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client


class Stickers:
    async def get_my_sticker_sets(self: "Client") -> StickerSets:
        """Installed sticker sets (``getMyStickerSets``). [HTTP]"""
        return await self.invoke(GetMyStickerSets())

    async def get_sticker_set_by_id(self: "Client", sticker_set_id: str) -> StickerSetResult:
        return await self.invoke(GetStickerSetByID(sticker_set_id=sticker_set_id))

    async def get_stickers_by_set_ids(self: "Client", sticker_set_ids: Sequence[str]) -> StickerSets:
        return await self.invoke(GetStickersBySetIDs(sticker_set_ids=list(sticker_set_ids)))

    async def get_stickers_by_emoji(self: "Client", emoji_character: str, *, suggest_by: str = "All") -> StickerSets:
        return await self.invoke(GetStickersByEmoji(emoji_character=emoji_character, suggest_by=suggest_by))

    async def search_stickers(self: "Client", search_text: str, start_id: Optional[str] = None) -> StickerSets:
        return await self.invoke(SearchStickers(search_text=search_text, start_id=start_id))

    async def get_trend_sticker_sets(self: "Client", start_id: Optional[str] = None) -> StickerSets:
        return await self.invoke(GetTrendStickerSets(start_id=start_id))

    async def get_my_archived_sticker_sets(self: "Client", *, search_text: Optional[str] = None, start_id: Optional[str] = None) -> StickerSets:
        return await self.invoke(GetMyArchivedStickerSets(search_text=search_text, start_id=start_id))

    async def action_on_sticker_set(self: "Client", sticker_set_id: str, action: Any) -> Empty:
        """``actionOnStickerSet`` (``Add`` / ``Remove``). [HTTP]"""
        return await self.invoke(ActionOnStickerSet(sticker_set_id=sticker_set_id, action=str(getattr(action, "value", action))))

    async def add_sticker_set(self: "Client", sticker_set_id: str) -> Empty:
        return await self.action_on_sticker_set(sticker_set_id, "Add")

    async def remove_sticker_set(self: "Client", sticker_set_id: str) -> Empty:
        return await self.action_on_sticker_set(sticker_set_id, "Remove")

    async def get_sticker_setting(self: "Client") -> StickerSetting:
        return await self.invoke(GetStickerSetting())

    async def send_sticker(self: "Client", object_guid: Any, sticker: Any, *, reply_to_message_id: Optional[str] = None) -> Any:
        """Send a sticker object (from a sticker set or a received message). [HTTP]"""
        payload = sticker.to_dict() if hasattr(sticker, "to_dict") else dict(sticker)
        return await self.send_message(object_guid, sticker=payload, reply_to_message_id=reply_to_message_id)

    async def get_my_gif_set(self: "Client") -> GifSet:
        return await self.invoke(GetMyGifSet())

    async def add_to_my_gif_set(self: "Client", object_guid: Any, message_id: Any) -> RawObject:
        return await self.invoke(AddToMyGifSet(object_guid=self._resolve_object_guid(object_guid), message_id=str(message_id)))

    # -- folders ------------------------------------------------------------------

    async def get_folders(self: "Client", last_state: Optional[int] = None) -> FoldersResult:
        """Chat folders (``getFolders``); the state is persisted. [HTTP]"""
        if last_state is None:
            last_state = await self.storage.folders_state()
        result = await self.invoke(GetFolders(last_state=last_state))
        if result.new_state is not None:
            await self.storage.set_folders_state(result.new_state)
        return result

    async def get_suggested_folders(self: "Client") -> FoldersResult:
        return await self.invoke(GetSuggestedFolders())

    async def add_folder(
        self: "Client",
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
        self: "Client",
        folder_id: str,
        *,
        name: Optional[str] = None,
        include_chat_types: Sequence[Any] | None = None,
        exclude_chat_types: Sequence[Any] | None = None,
        include_object_guids: Sequence[Any] | None = None,
        exclude_object_guids: Sequence[Any] | None = None,
    ) -> FolderResult:
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

    async def delete_folder(self: "Client", folder_id: str) -> FolderResult:
        return await self.invoke(DeleteFolder(folder_id=folder_id))

    async def set_pin_chat_in_folder(self: "Client", folder_id: str, object_guid: Any, action: Any = "Pin") -> RawObject:
        return await self.invoke(SetPinChatInFolder(folder_id=folder_id, object_guid=self._resolve_object_guid(object_guid), action=str(getattr(action, "value", action))))


__all__ = ["Stickers"]
