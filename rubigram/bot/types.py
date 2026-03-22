from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from rubigram.types.object import Object

from .enums import (
    ButtonCalendarType,
    ButtonLocationType,
    ButtonSelectionGet,
    ButtonSelectionSearch,
    ButtonSelectionType,
    ButtonTextboxTypeKeypad,
    ButtonTextboxTypeLine,
    ButtonType,
    ChatKeypadType,
    ChatType,
    FileType,
    ForwardedFromType,
    MessageSender,
    PollStatusState,
    ChatType,
    UpdateEndpointType,
    UpdateType,
)


def _enum_or_value(enum_cls: type, value: Any) -> Any:
    if value is None:
        return None
    try:
        return enum_cls(value)
    except Exception:
        return value


def _parse_unknown(client: Any, value: Any) -> Any:
    if isinstance(value, dict):
        return GenericObject._parse(client, value)
    if isinstance(value, list):
        return [_parse_unknown(client, item) for item in value]
    return value


def _apply_unknown_fields(target: Object, client: Any, data: dict[str, Any], known_fields: set[str]) -> None:
    for key, value in data.items():
        if key not in known_fields:
            setattr(target, key, _parse_unknown(client, value))


class GenericObject(Object):
    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def _parse(cls, client: Any, data: Any) -> Any:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        if isinstance(data, list):
            return [_parse_unknown(client, item) for item in data]
        if not isinstance(data, dict):
            return data
        return cls(client=client, **{key: _parse_unknown(client, value) for key, value in data.items()})


@dataclass
class File(Object):
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    size: Optional[str] = None

    def __init__(self, *, client: Any = None, file_id: str | None = None, file_name: str | None = None, size: str | None = None):
        super().__init__(client)
        self.file_id = file_id
        self.file_name = file_name
        self.size = size

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["File"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, file_id=data.get("file_id"), file_name=data.get("file_name"), size=data.get("size"))
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Chat(Object):
    chat_id: Optional[str] = None
    chat_type: Optional[ChatType | str] = None
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    username: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.chat_id = kwargs.get("chat_id")
        self.chat_type = _enum_or_value(ChatType, kwargs.get("chat_type"))
        self.user_id = kwargs.get("user_id")
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.title = kwargs.get("title")
        self.username = kwargs.get("username")

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Chat"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ForwardedFrom(Object):
    type_from: Optional[ForwardedFromType | str] = None
    message_id: Optional[str] = None
    from_chat_id: Optional[str] = None
    from_sender_id: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.type_from = _enum_or_value(ForwardedFromType, kwargs.get("type_from"))
        self.message_id = kwargs.get("message_id")
        self.from_chat_id = kwargs.get("from_chat_id")
        self.from_sender_id = kwargs.get("from_sender_id")

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ForwardedFrom"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class MessageTextUpdate(Object):
    message_id: Optional[str] = None
    text: Optional[str] = None

    def __init__(self, *, client: Any = None, message_id: str | None = None, text: str | None = None):
        super().__init__(client)
        self.message_id = message_id
        self.text = text

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["MessageTextUpdate"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, message_id=data.get("message_id"), text=data.get("text"))
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class BotCommand(Object):
    command: Optional[str] = None
    description: Optional[str] = None

    def __init__(self, *, client: Any = None, command: str | None = None, description: str | None = None):
        super().__init__(client)
        self.command = command
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        return {"command": self.command, "description": self.description}

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["BotCommand"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, command=data.get("command"), description=data.get("description"))
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Bot(Object):
    bot_id: Optional[str] = None
    bot_title: Optional[str] = None
    avatar: Optional[File] = None
    description: Optional[str] = None
    username: Optional[str] = None
    start_message: Optional[str] = None
    share_url: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.bot_id = kwargs.get("bot_id")
        self.bot_title = kwargs.get("bot_title")
        self.avatar = File._parse(client, kwargs.get("avatar"))
        self.description = kwargs.get("description")
        self.username = kwargs.get("username")
        self.start_message = kwargs.get("start_message")
        self.share_url = kwargs.get("share_url")

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Bot"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Sticker(Object):
    sticker_id: Optional[str] = None
    file: Optional[File] = None
    emoji_character: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.sticker_id = kwargs.get("sticker_id")
        self.file = File._parse(client, kwargs.get("file"))
        self.emoji_character = kwargs.get("emoji_character")

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Sticker"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ContactMessage(Object):
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.phone_number = kwargs.get("phone_number")
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ContactMessage"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class PollStatus(Object):
    state: Optional[PollStatusState | str] = None
    selection_index: Optional[int] = None
    percent_vote_options: list[int] = field(default_factory=list)
    total_vote: Optional[int] = None
    show_total_votes: Optional[bool] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.state = _enum_or_value(PollStatusState, kwargs.get("state"))
        self.selection_index = kwargs.get("selection_index")
        self.percent_vote_options = list(kwargs.get("percent_vote_options") or [])
        self.total_vote = kwargs.get("total_vote")
        self.show_total_votes = kwargs.get("show_total_votes")

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["PollStatus"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Poll(Object):
    question: Optional[str] = None
    options: list[str] = field(default_factory=list)
    poll_status: Optional[PollStatus] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.question = kwargs.get("question")
        self.options = list(kwargs.get("options") or [])
        self.poll_status = PollStatus._parse(client, kwargs.get("poll_status"))

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Poll"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Location(Object):
    longitude: Optional[str] = None
    latitude: Optional[str] = None

    def __init__(self, *, client: Any = None, longitude: str | None = None, latitude: str | None = None):
        super().__init__(client)
        self.longitude = longitude
        self.latitude = latitude

    def to_dict(self) -> dict[str, Any]:
        return {"longitude": self.longitude, "latitude": self.latitude}

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Location"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, longitude=data.get("longitude"), latitude=data.get("latitude"))
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ButtonSelectionItem(Object):
    text: Optional[str] = None
    image_url: Optional[str] = None
    type: Optional[ButtonSelectionType | str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.text = kwargs.get("text")
        self.image_url = kwargs.get("image_url")
        self.type = _enum_or_value(ButtonSelectionType, kwargs.get("type"))

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "image_url": self.image_url, "type": str(self.type) if self.type is not None else None}

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ButtonSelectionItem"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ButtonSelection(Object):
    selection_id: Optional[str] = None
    search_type: Optional[ButtonSelectionSearch | str] = None
    get_type: Optional[ButtonSelectionGet | str] = None
    items: list[ButtonSelectionItem] = field(default_factory=list)
    is_multi_selection: Optional[bool] = None
    columns_count: Optional[str] = None
    title: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.selection_id = kwargs.get("selection_id")
        self.search_type = _enum_or_value(ButtonSelectionSearch, kwargs.get("search_type"))
        self.get_type = _enum_or_value(ButtonSelectionGet, kwargs.get("get_type"))
        self.items = [ButtonSelectionItem._parse(client, item) for item in kwargs.get("items", [])]
        self.is_multi_selection = kwargs.get("is_multi_selection")
        self.columns_count = kwargs.get("columns_count")
        self.title = kwargs.get("title")

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "search_type": str(self.search_type) if self.search_type is not None else None,
            "get_type": str(self.get_type) if self.get_type is not None else None,
            "items": [item.to_dict() for item in self.items],
            "is_multi_selection": self.is_multi_selection,
            "columns_count": self.columns_count,
            "title": self.title,
        }

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ButtonSelection"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ButtonCalendar(Object):
    default_value: Optional[str] = None
    type: Optional[ButtonCalendarType | str] = None
    min_year: Optional[str] = None
    max_year: Optional[str] = None
    title: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.default_value = kwargs.get("default_value")
        self.type = _enum_or_value(ButtonCalendarType, kwargs.get("type"))
        self.min_year = kwargs.get("min_year")
        self.max_year = kwargs.get("max_year")
        self.title = kwargs.get("title")

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_value": self.default_value,
            "type": str(self.type) if self.type is not None else None,
            "min_year": self.min_year,
            "max_year": self.max_year,
            "title": self.title,
        }

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ButtonCalendar"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ButtonNumberPicker(Object):
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    default_value: Optional[str] = None
    title: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.min_value = kwargs.get("min_value")
        self.max_value = kwargs.get("max_value")
        self.default_value = kwargs.get("default_value")
        self.title = kwargs.get("title")

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
            "default_value": self.default_value,
            "title": self.title,
        }

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ButtonNumberPicker"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ButtonStringPicker(Object):
    items: list[str] = field(default_factory=list)
    default_value: Optional[str] = None
    title: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.items = list(kwargs.get("items") or [])
        self.default_value = kwargs.get("default_value")
        self.title = kwargs.get("title")

    def to_dict(self) -> dict[str, Any]:
        return {"items": self.items, "default_value": self.default_value, "title": self.title}

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ButtonStringPicker"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ButtonTextbox(Object):
    type_line: Optional[ButtonTextboxTypeLine | str] = None
    type_keypad: Optional[ButtonTextboxTypeKeypad | str] = None
    place_holder: Optional[str] = None
    title: Optional[str] = None
    default_value: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.type_line = _enum_or_value(ButtonTextboxTypeLine, kwargs.get("type_line"))
        self.type_keypad = _enum_or_value(ButtonTextboxTypeKeypad, kwargs.get("type_keypad"))
        self.place_holder = kwargs.get("place_holder")
        self.title = kwargs.get("title")
        self.default_value = kwargs.get("default_value")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type_line": str(self.type_line) if self.type_line is not None else None,
            "type_keypad": str(self.type_keypad) if self.type_keypad is not None else None,
            "place_holder": self.place_holder,
            "title": self.title,
            "default_value": self.default_value,
        }

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ButtonTextbox"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class ButtonLocation(Object):
    default_pointer_location: Optional[Location] = None
    default_map_location: Optional[Location] = None
    type: Optional[ButtonLocationType | str] = None
    title: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.default_pointer_location = Location._parse(client, kwargs.get("default_pointer_location"))
        self.default_map_location = Location._parse(client, kwargs.get("default_map_location"))
        self.type = _enum_or_value(ButtonLocationType, kwargs.get("type"))
        self.title = kwargs.get("title")

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_pointer_location": self.default_pointer_location.to_dict() if self.default_pointer_location else None,
            "default_map_location": self.default_map_location.to_dict() if self.default_map_location else None,
            "type": str(self.type) if self.type is not None else None,
            "title": self.title,
        }

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ButtonLocation"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class AuxData(Object):
    start_id: Optional[str] = None
    button_id: Optional[str] = None

    def __init__(self, *, client: Any = None, start_id: str | None = None, button_id: str | None = None):
        super().__init__(client)
        self.start_id = start_id
        self.button_id = button_id

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["AuxData"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, start_id=data.get("start_id"), button_id=data.get("button_id"))
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Button(Object):
    id: Optional[str] = None
    type: Optional[ButtonType | str] = None
    button_text: Optional[str] = None
    button_selection: Optional[ButtonSelection] = None
    button_calendar: Optional[ButtonCalendar] = None
    button_number_picker: Optional[ButtonNumberPicker] = None
    button_string_picker: Optional[ButtonStringPicker] = None
    button_location: Optional[ButtonLocation] = None
    button_textbox: Optional[ButtonTextbox] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.id = kwargs.get("id")
        self.type = _enum_or_value(ButtonType, kwargs.get("type"))
        self.button_text = kwargs.get("button_text")
        self.button_selection = ButtonSelection._parse(client, kwargs.get("button_selection"))
        self.button_calendar = ButtonCalendar._parse(client, kwargs.get("button_calendar"))
        self.button_number_picker = ButtonNumberPicker._parse(client, kwargs.get("button_number_picker"))
        self.button_string_picker = ButtonStringPicker._parse(client, kwargs.get("button_string_picker"))
        self.button_location = ButtonLocation._parse(client, kwargs.get("button_location"))
        self.button_textbox = ButtonTextbox._parse(client, kwargs.get("button_textbox"))

    def to_dict(self) -> dict[str, Any]:
        data = {"id": self.id, "type": str(self.type) if self.type is not None else None, "button_text": self.button_text}
        optional_fields = {
            "button_selection": self.button_selection.to_dict() if self.button_selection else None,
            "button_calendar": self.button_calendar.to_dict() if self.button_calendar else None,
            "button_number_picker": self.button_number_picker.to_dict() if self.button_number_picker else None,
            "button_string_picker": self.button_string_picker.to_dict() if self.button_string_picker else None,
            "button_location": self.button_location.to_dict() if self.button_location else None,
            "button_textbox": self.button_textbox.to_dict() if self.button_textbox else None,
        }
        data.update({key: value for key, value in optional_fields.items() if value is not None})
        return data

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Button"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class KeypadRow(Object):
    buttons: list[Button] = field(default_factory=list)

    def __init__(self, *, client: Any = None, buttons: Optional[list[Any]] = None):
        super().__init__(client)
        self.buttons = [Button._parse(client, button) for button in buttons or []]

    def to_dict(self) -> dict[str, Any]:
        return {"buttons": [button.to_dict() for button in self.buttons]}

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["KeypadRow"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, buttons=data.get("buttons"))
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Keypad(Object):
    rows: list[KeypadRow] = field(default_factory=list)
    resize_keyboard: Optional[bool] = None
    one_time_keyboard: Optional[bool] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.rows = [KeypadRow._parse(client, row) for row in kwargs.get("rows", [])]
        self.resize_keyboard = kwargs.get("resize_keyboard")
        self.one_time_keyboard = kwargs.get("one_time_keyboard")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"rows": [row.to_dict() for row in self.rows]}
        if self.resize_keyboard is not None:
            data["resize_keyboard"] = self.resize_keyboard
        if self.one_time_keyboard is not None:
            data["one_time_keyboard"] = self.one_time_keyboard
        return data

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Keypad"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class MessageKeypadUpdate(Object):
    message_id: Optional[str] = None
    inline_keypad: Optional[Keypad] = None

    def __init__(self, *, client: Any = None, message_id: str | None = None, inline_keypad: Any = None):
        super().__init__(client)
        self.message_id = message_id
        self.inline_keypad = Keypad._parse(client, inline_keypad)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "inline_keypad": self.inline_keypad.to_dict() if self.inline_keypad else None,
        }

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["MessageKeypadUpdate"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, message_id=data.get("message_id"), inline_keypad=data.get("inline_keypad"))
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class Message(Object):
    message_id: Optional[str] = None
    text: Optional[str] = None
    time: Optional[int] = None
    is_edited: Optional[bool] = None
    sender_type: Optional[MessageSender | str] = None
    sender_id: Optional[str] = None
    aux_data: Optional[AuxData] = None
    file: Optional[File] = None
    reply_to_message_id: Optional[str] = None
    forwarded_from: Optional[ForwardedFrom] = None
    forwarded_no_link: Optional[str] = None
    location: Optional[Location] = None
    sticker: Optional[Sticker] = None
    contact_message: Optional[ContactMessage] = None
    poll: Optional[Poll] = None
    chat_id: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.message_id = kwargs.get("message_id")
        self.text = kwargs.get("text")
        self.time = kwargs.get("time")
        self.is_edited = kwargs.get("is_edited")
        self.sender_type = _enum_or_value(MessageSender, kwargs.get("sender_type"))
        self.sender_id = kwargs.get("sender_id")
        self.aux_data = AuxData._parse(client, kwargs.get("aux_data"))
        self.file = File._parse(client, kwargs.get("file"))
        self.reply_to_message_id = kwargs.get("reply_to_message_id")
        self.forwarded_from = ForwardedFrom._parse(client, kwargs.get("forwarded_from"))
        self.forwarded_no_link = kwargs.get("forwarded_no_link")
        self.location = Location._parse(client, kwargs.get("location"))
        self.sticker = Sticker._parse(client, kwargs.get("sticker"))
        self.contact_message = ContactMessage._parse(client, kwargs.get("contact_message"))
        self.poll = Poll._parse(client, kwargs.get("poll"))
        self.chat_id = kwargs.get("chat_id")
        self.type = kwargs.get("type") or self._infer_message_type()
        self.chat_type = kwargs.get("chat_type") or self._infer_chat_type()
        self.is_mine = bool(kwargs.get("is_mine", False))

    def _infer_message_type(self) -> str:
        if self.poll is not None:
            return "Poll"
        if self.sticker is not None:
            return "Sticker"
        if self.location is not None:
            return "Location"
        if self.contact_message is not None:
            return "Contact"
        if self.file is not None:
            return "File"
        if self.text:
            return "Text"
        return "Unknown"

    def _infer_chat_type(self) -> ChatType | str:
        if self.sender_type == MessageSender.BOT:
            return ChatType.BOT
        return ChatType.USER

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]], *, chat_id: str | None = None) -> Optional["Message"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            if chat_id is not None and data.chat_id is None:
                data.chat_id = chat_id
            return data
        payload = dict(data)
        if chat_id is not None and payload.get("chat_id") is None:
            payload["chat_id"] = chat_id
        result = cls(client=client, **payload)
        _apply_unknown_fields(result, client, payload, set(result.__dict__.keys()))
        return result

    async def reply(
        self,
        text: str,
        *,
        inline_keypad: Optional["Keypad"] = None,
        chat_keypad: Optional["Keypad"] = None,
        chat_keypad_type: Optional[ChatKeypadType | str] = None,
        disable_notification: bool = False,
    ) -> "SentMessage":
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")
        if not self.chat_id:
            raise RuntimeError("This message does not have chat_id")
        return await self._client.send_message(
            self.chat_id,
            text,
            inline_keypad=inline_keypad,
            chat_keypad=chat_keypad,
            chat_keypad_type=chat_keypad_type,
            disable_notification=disable_notification,
            reply_to_message_id=self.message_id,
        )

    async def delete(self) -> bool:
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")
        if not self.chat_id or not self.message_id:
            raise RuntimeError("This message is missing chat_id or message_id")
        return await self._client.delete_message(self.chat_id, self.message_id)

    async def edit_text(self, text: str) -> "SentMessage":
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")
        if not self.chat_id or not self.message_id:
            raise RuntimeError("This message is missing chat_id or message_id")
        return await self._client.edit_message_text(self.chat_id, self.message_id, text)


@dataclass
class Update(Object):
    type: Optional[UpdateType | str] = None
    chat_id: Optional[str] = None
    removed_message_id: Optional[str] = None
    new_message: Optional[Message] = None
    updated_message: Optional[Message] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.type = _enum_or_value(UpdateType, kwargs.get("type"))
        self.chat_id = kwargs.get("chat_id")
        self.removed_message_id = kwargs.get("removed_message_id")
        self.new_message = Message._parse(client, kwargs.get("new_message"), chat_id=self.chat_id)
        self.updated_message = Message._parse(client, kwargs.get("updated_message"), chat_id=self.chat_id)

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Update"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class InlineMessage(Object):
    sender_id: Optional[str] = None
    text: Optional[str] = None
    file: Optional[File] = None
    location: Optional[Location] = None
    aux_data: Optional[AuxData] = None
    message_id: Optional[str] = None
    chat_id: Optional[str] = None

    def __init__(self, *, client: Any = None, **kwargs: Any):
        super().__init__(client)
        self.sender_id = kwargs.get("sender_id")
        self.text = kwargs.get("text")
        self.file = File._parse(client, kwargs.get("file"))
        self.location = Location._parse(client, kwargs.get("location"))
        self.aux_data = AuxData._parse(client, kwargs.get("aux_data"))
        self.message_id = kwargs.get("message_id")
        self.chat_id = kwargs.get("chat_id")

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["InlineMessage"]:
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        result = cls(client=client, **data)
        _apply_unknown_fields(result, client, data, set(result.__dict__.keys()))
        return result


@dataclass
class SentMessage(Object):
    message_id: Optional[str] = None

    def __init__(self, *, client: Any = None, message_id: str | None = None, **kwargs: Any):
        super().__init__(client)
        self.message_id = message_id
        for key, value in kwargs.items():
            setattr(self, key, _parse_unknown(client, value))

    @classmethod
    def _parse(cls, client: Any, data: Any) -> "SentMessage":
        if isinstance(data, cls):
            data.bind(client)
            return data
        if isinstance(data, dict):
            payload = dict(data)
            return cls(client=client, message_id=payload.pop("message_id", None) or payload.pop("new_message_id", None), **payload)
        if isinstance(data, str):
            return cls(client=client, message_id=data)
        return cls(client=client)


@dataclass
class BotUpdates(Object):
    updates: list[Update] = field(default_factory=list)
    next_offset_id: Optional[str] = None

    def __init__(self, *, client: Any = None, updates: Optional[list[Any]] = None, next_offset_id: str | None = None, **kwargs: Any):
        super().__init__(client)
        self.updates = [Update._parse(client, item) for item in updates or []]
        self.next_offset_id = next_offset_id
        for key, value in kwargs.items():
            if key not in {"updates", "next_offset_id"}:
                setattr(self, key, _parse_unknown(client, value))

    @classmethod
    def _parse(cls, client: Any, data: Any) -> "BotUpdates":
        if isinstance(data, cls):
            data.bind(client)
            return data
        if not isinstance(data, dict):
            return cls(client=client)
        payload = dict(data)
        updates = payload.pop("updates", None)
        next_offset_id = payload.pop("next_offset_id", None)
        return cls(client=client, updates=updates, next_offset_id=next_offset_id, **payload)


@dataclass
class WebhookUpdate(Object):
    update: Optional[Update] = None
    inline_message: Optional[InlineMessage] = None

    def __init__(self, *, client: Any = None, update: Any = None, inline_message: Any = None, **kwargs: Any):
        super().__init__(client)
        self.update = Update._parse(client, update)
        self.inline_message = InlineMessage._parse(client, inline_message)
        for key, value in kwargs.items():
            if key not in {"update", "inline_message"}:
                setattr(self, key, _parse_unknown(client, value))

    @classmethod
    def _parse(cls, client: Any, data: Any) -> "WebhookUpdate":
        if isinstance(data, cls):
            data.bind(client)
            return data
        if not isinstance(data, dict):
            return cls(client=client)
        payload = dict(data)
        update = payload.pop("update", None)
        inline_message = payload.pop("inline_message", None)
        return cls(client=client, update=update, inline_message=inline_message, **payload)


__all__ = [
    "AuxData",
    "Bot",
    "BotCommand",
    "BotUpdates",
    "Button",
    "ButtonCalendar",
    "ButtonLocation",
    "ButtonNumberPicker",
    "ButtonSelection",
    "ButtonSelectionItem",
    "ButtonStringPicker",
    "ButtonTextbox",
    "Chat",
    "ContactMessage",
    "File",
    "ForwardedFrom",
    "GenericObject",
    "InlineMessage",
    "Keypad",
    "KeypadRow",
    "Location",
    "Message",
    "MessageKeypadUpdate",
    "MessageTextUpdate",
    "Poll",
    "PollStatus",
    "SentMessage",
    "Sticker",
    "Update",
    "WebhookUpdate",
]
