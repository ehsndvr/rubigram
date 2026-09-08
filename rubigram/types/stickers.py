"""Sticker sets, stickers, GIF sets, reactions and polls."""

from __future__ import annotations

from typing import Any, Optional

from .files import FileInline, Sticker
from .object import Object, model
from .user import PeerObject


@model
class StickerSet(Object):
    sticker_set_id: Optional[str] = None
    title: Optional[str] = None
    count_stickers: Optional[int] = None
    top_stickers: list[Sticker] = None  # type: ignore[assignment]
    stickers: list[Sticker] = None  # type: ignore[assignment]
    share_string: Optional[str] = None
    is_installed: Optional[bool] = None
    is_archived: Optional[bool] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.top_stickers = self.top_stickers or []
        self.stickers = self.stickers or []


@model
class StickerSets(Object):
    """Result of ``getMyStickerSets`` / ``getTrendStickerSets`` / ``searchStickers`` … ."""

    sticker_sets: list[StickerSet] = None  # type: ignore[assignment]
    stickers: list[Sticker] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.sticker_sets = self.sticker_sets or []
        self.stickers = self.stickers or []


@model
class StickerSetResult(Object):
    sticker_set: Optional[StickerSet] = None
    timestamp: Optional[str] = None


@model
class StickerSetting(Object):
    sticker_setting: Optional[Any] = None


@model
class GifSet(Object):
    gifs: list[FileInline] = None  # type: ignore[assignment]
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.gifs = self.gifs or []


@model
class AvailableReaction(Object):
    reaction_id: Optional[int] = None
    emoji_char: Optional[str] = None
    name: Optional[str] = None


@model
class AvailableReactions(Object):
    reactions: list[AvailableReaction] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.reactions = self.reactions or []

    def __iter__(self):
        return iter(self.reactions)

    def __len__(self) -> int:
        return len(self.reactions)


@model
class UserMessageReaction(Object):
    user_guid: Optional[str] = None
    reaction_id: Optional[int] = None
    emoji_char: Optional[str] = None
    abs_user: Optional[PeerObject] = None


@model
class MessageReactions(Object):
    user_message_reactions: list[UserMessageReaction] = None  # type: ignore[assignment]
    reactions: list[Any] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.user_message_reactions = self.user_message_reactions or []
        self.reactions = self.reactions or []


@model
class ChatReactions(Object):
    reactions: list[Any] = None  # type: ignore[assignment]
    chat_reaction_setting: Optional[Any] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.reactions = self.reactions or []


@model
class PollStatus(Object):
    state: Optional[str] = None
    selection_index: Optional[int] = None
    percent_vote_options: list[int] = None  # type: ignore[assignment]
    total_vote: Optional[int] = None
    show_total_votes: Optional[bool] = None
    multiple_selections: list[int] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.percent_vote_options = self.percent_vote_options or []
        self.multiple_selections = self.multiple_selections or []


@model
class Poll(Object):
    poll_id: Optional[str] = None
    question: Optional[str] = None
    options: list[str] = None  # type: ignore[assignment]
    type: Optional[str] = None
    is_anonymous: Optional[bool] = None
    allows_multiple_answers: Optional[bool] = None
    correct_option_index: Optional[int] = None
    explanation: Optional[str] = None
    poll_status: Optional[PollStatus] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.options = self.options or []


@model
class PollStatusResult(Object):
    poll_status: Optional[PollStatus] = None
    timestamp: Optional[str] = None


@model
class PollOptionVoters(Object):
    voters: list[PeerObject] = None  # type: ignore[assignment]
    has_continue: Optional[bool] = None
    next_start_id: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.voters = self.voters or []


__all__ = [
    "AvailableReaction",
    "AvailableReactions",
    "ChatReactions",
    "GifSet",
    "MessageReactions",
    "Poll",
    "PollOptionVoters",
    "PollStatus",
    "PollStatusResult",
    "StickerSet",
    "StickerSetResult",
    "StickerSets",
    "StickerSetting",
    "UserMessageReaction",
]
