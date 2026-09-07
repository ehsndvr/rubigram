"""Enumerations of the Rubika (user) API, taken from web.rubika.ir 4.4.34."""

from __future__ import annotations

from enum import Enum


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ChatType(_StringEnum):
    """``abs_object.type`` / ``chat_update.type`` values."""

    USER = "User"
    BOT = "Bot"
    GROUP = "Group"
    CHANNEL = "Channel"
    SERVICE = "Service"


class MessageType(_StringEnum):
    TEXT = "Text"
    FILE_INLINE = "FileInline"
    FILE_INLINE_CAPTION = "FileInlineCaption"
    STICKER = "Sticker"
    RUBINO_POST = "RubinoPost"
    LIVE = "Live"
    POLL = "Poll"
    QUIZ = "Poll3"
    EVENT = "Event"
    LOCATION = "Location"
    CONTACT = "ContactMessage"
    CALL = "Call"
    WALLET_TRANSFER = "WalletTransfer"
    PAYMENT = "Payment"


class FileInlineType(_StringEnum):
    FILE = "File"
    IMAGE = "Image"
    VIDEO = "Video"
    GIF = "Gif"
    VOICE = "Voice"
    MUSIC = "Music"


class ActivityType(_StringEnum):
    """``sendChatActivity`` / ``show_activities`` values."""

    TYPING = "Typing"
    RECORDING = "Recording"
    UPLOADING = "Uploading"


class UpdateAction(_StringEnum):
    """``action`` of message and chat updates."""

    NEW = "New"
    EDIT = "Edit"
    DELETE = "Delete"


class SortOrder(_StringEnum):
    FROM_MAX = "FromMax"
    FROM_MIN = "FromMin"


class DeleteType(_StringEnum):
    GLOBAL = "Global"
    LOCAL = "Local"


class SearchType(_StringEnum):
    TEXT = "Text"
    HASHTAG = "Hashtag"


class PinAction(_StringEnum):
    PIN = "Pin"
    UNPIN = "Unpin"


class ReactionAction(_StringEnum):
    ADD = "Add"
    REMOVE = "Remove"


class BlockAction(_StringEnum):
    BLOCK = "Block"
    UNBLOCK = "Unblock"


class MemberAction(_StringEnum):
    """``banGroupMember`` / ``banChannelMember`` action."""

    SET = "Set"
    UNSET = "Unset"


class AdminAction(_StringEnum):
    SET_ADMIN = "SetAdmin"
    UNSET_ADMIN = "UnsetAdmin"


class JoinChannelAction(_StringEnum):
    JOIN = "Join"
    LEAVE = "Leave"
    REMOVE = "Remove"


class JoinRequestAction(_StringEnum):
    ACCEPT = "Accept"
    REJECT = "Reject"


class OwnerRequestAction(_StringEnum):
    ACCEPT = "Accept"
    REJECT = "Reject"


class StickerSetAction(_StringEnum):
    ADD = "Add"
    REMOVE = "Remove"


class ChatAction(_StringEnum):
    """``setActionChat`` actions."""

    MUTE = "Mute"
    UNMUTE = "Unmute"
    PIN = "Pin"
    UNPIN = "Unpin"
    ARCHIVE = "Archive"
    UNARCHIVE = "Unarchive"


class DraftAction(_StringEnum):
    ALL = "All"
    CHAT = "Chat"


class FolderChatType(_StringEnum):
    CONTACTS = "Contacts"
    NON_CONTACTS = "NonConatcts"  # sic: the server spells it this way
    GROUPS = "Groups"
    CHANNELS = "Channels"
    BOTS = "Bots"
    SERVICES = "Services"


class ChannelType(_StringEnum):
    PUBLIC = "Public"
    PRIVATE = "Private"


class ChatHistoryVisibility(_StringEnum):
    VISIBLE = "Visible"
    HIDDEN = "Hidden"


class ReactionType(_StringEnum):
    ALL = "All"
    SELECTED = "Selected"
    DISABLED = "Disabled"


class SendCodeType(_StringEnum):
    SMS = "SMS"
    INTERNAL = "Internal"


class PollType(_StringEnum):
    REGULAR = "Regular"
    QUIZ = "Quiz"


__all__ = [
    "ActivityType",
    "AdminAction",
    "BlockAction",
    "ChannelType",
    "ChatAction",
    "ChatHistoryVisibility",
    "ChatType",
    "DeleteType",
    "DraftAction",
    "FileInlineType",
    "FolderChatType",
    "JoinChannelAction",
    "JoinRequestAction",
    "MemberAction",
    "MessageType",
    "OwnerRequestAction",
    "PinAction",
    "PollType",
    "ReactionAction",
    "ReactionType",
    "SearchType",
    "SendCodeType",
    "SortOrder",
    "StickerSetAction",
    "UpdateAction",
]
