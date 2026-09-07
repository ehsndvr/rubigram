"""Enumerations of the Rubika Bot API."""

from __future__ import annotations

from enum import Enum


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class BotChatType(_StringEnum):
    USER = "User"
    BOT = "Bot"
    GROUP = "Group"
    CHANNEL = "Channel"


class FileType(_StringEnum):
    FILE = "File"
    IMAGE = "Image"
    VOICE = "Voice"
    VIDEO = "Video"
    MUSIC = "Music"
    GIF = "Gif"


class ForwardedFromType(_StringEnum):
    USER = "User"
    CHANNEL = "Channel"
    BOT = "Bot"


class PollStatusState(_StringEnum):
    OPEN = "Open"
    CLOSED = "Closed"


class ButtonSelectionType(_StringEnum):
    TEXT_ONLY = "TextOnly"
    TEXT_IMG_THU = "TextImgThu"
    TEXT_IMG_BIG = "TextImgBig"


class ButtonSelectionSearch(_StringEnum):
    NONE = "None"
    LOCAL = "Local"
    API = "Api"


class ButtonSelectionGet(_StringEnum):
    LOCAL = "Local"
    API = "Api"


class ButtonCalendarType(_StringEnum):
    DATE_PERSIAN = "DatePersian"
    DATE_GREGORIAN = "DateGregorian"


class ButtonTextboxTypeKeypad(_StringEnum):
    STRING = "String"
    NUMBER = "Number"


class ButtonTextboxTypeLine(_StringEnum):
    SINGLE_LINE = "SingleLine"
    MULTI_LINE = "MultiLine"


class ButtonLocationType(_StringEnum):
    PICKER = "Picker"
    VIEW = "View"


class ButtonType(_StringEnum):
    SIMPLE = "Simple"
    SELECTION = "Selection"
    CALENDAR = "Calendar"
    NUMBER_PICKER = "NumberPicker"
    STRING_PICKER = "StringPicker"
    LOCATION = "Location"
    CAMERA_IMAGE = "CameraImage"
    CAMERA_VIDEO = "CameraVideo"
    GALLERY_IMAGE = "GalleryImage"
    GALLERY_VIDEO = "GalleryVideo"
    FILE = "File"
    AUDIO = "Audio"
    RECORD_AUDIO = "RecordAudio"
    TEXTBOX = "Textbox"
    LINK = "Link"
    ASK_MY_PHONE_NUMBER = "AskMyPhoneNumber"
    ASK_MY_LOCATION = "AskMyLocation"
    BARCODE = "Barcode"


class MessageSender(_StringEnum):
    USER = "User"
    BOT = "Bot"


class UpdateType(_StringEnum):
    UPDATED_MESSAGE = "UpdatedMessage"
    NEW_MESSAGE = "NewMessage"
    REMOVED_MESSAGE = "RemovedMessage"
    STARTED_BOT = "StartedBot"
    STOPPED_BOT = "StoppedBot"


class ChatKeypadType(_StringEnum):
    NONE = "None"
    NEW = "New"
    REMOVE = "Remove"


class UpdateEndpointType(_StringEnum):
    RECEIVE_UPDATE = "ReceiveUpdate"
    RECEIVE_INLINE_MESSAGE = "ReceiveInlineMessage"
    RECEIVE_QUERY = "ReceiveQuery"
    GET_SELECTION_ITEM = "GetSelectionItem"
    SEARCH_SELECTION_ITEMS = "SearchSelectionItems"


# Name used by the old ``rubigram.bot.enums`` module.
ChatType = BotChatType

__all__ = [
    "BotChatType",
    "ButtonCalendarType",
    "ButtonLocationType",
    "ButtonSelectionGet",
    "ButtonSelectionSearch",
    "ButtonSelectionType",
    "ButtonTextboxTypeKeypad",
    "ButtonTextboxTypeLine",
    "ButtonType",
    "ChatKeypadType",
    "ChatType",
    "FileType",
    "ForwardedFromType",
    "MessageSender",
    "PollStatusState",
    "UpdateEndpointType",
    "UpdateType",
]
