"""Bot API keypads (inline and chat keyboards)."""

from __future__ import annotations

from typing import Any, Optional

from rubigram.enums.bot import (
    ButtonCalendarType,
    ButtonLocationType,
    ButtonSelectionGet,
    ButtonSelectionSearch,
    ButtonSelectionType,
    ButtonTextboxTypeKeypad,
    ButtonTextboxTypeLine,
    ButtonType,
)

from ..object import Object, model


@model
class Location(Object):
    longitude: Optional[str] = None
    latitude: Optional[str] = None


@model
class ButtonSelectionItem(Object):
    text: Optional[str] = None
    image_url: Optional[str] = None
    type: Optional[ButtonSelectionType] = None


@model
class ButtonSelection(Object):
    selection_id: Optional[str] = None
    search_type: Optional[ButtonSelectionSearch] = None
    get_type: Optional[ButtonSelectionGet] = None
    items: list[ButtonSelectionItem] = None  # type: ignore[assignment]
    is_multi_selection: Optional[bool] = None
    columns_count: Optional[str] = None
    title: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.items = self.items or []


@model
class ButtonCalendar(Object):
    default_value: Optional[str] = None
    type: Optional[ButtonCalendarType] = None
    min_year: Optional[str] = None
    max_year: Optional[str] = None
    title: Optional[str] = None


@model
class ButtonNumberPicker(Object):
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    default_value: Optional[str] = None
    title: Optional[str] = None


@model
class ButtonStringPicker(Object):
    items: list[str] = None  # type: ignore[assignment]
    default_value: Optional[str] = None
    title: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.items = self.items or []


@model
class ButtonTextbox(Object):
    type_line: Optional[ButtonTextboxTypeLine] = None
    type_keypad: Optional[ButtonTextboxTypeKeypad] = None
    place_holder: Optional[str] = None
    title: Optional[str] = None
    default_value: Optional[str] = None


@model
class ButtonLocation(Object):
    default_pointer_location: Optional[Location] = None
    default_map_location: Optional[Location] = None
    type: Optional[ButtonLocationType] = None
    title: Optional[str] = None


@model
class AuxData(Object):
    start_id: Optional[str] = None
    button_id: Optional[str] = None


@model
class Button(Object):
    id: Optional[str] = None
    type: Optional[ButtonType] = None
    button_text: Optional[str] = None
    button_selection: Optional[ButtonSelection] = None
    button_calendar: Optional[ButtonCalendar] = None
    button_number_picker: Optional[ButtonNumberPicker] = None
    button_string_picker: Optional[ButtonStringPicker] = None
    button_location: Optional[ButtonLocation] = None
    button_textbox: Optional[ButtonTextbox] = None

    @classmethod
    def simple(cls, id: str, text: str) -> "Button":
        return cls(id=id, type=ButtonType.SIMPLE, button_text=text)


@model
class KeypadRow(Object):
    buttons: list[Button] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.buttons = [Button._parse(client, button) if isinstance(button, dict) else button for button in (self.buttons or [])]


@model
class Keypad(Object):
    rows: list[KeypadRow] = None  # type: ignore[assignment]
    resize_keyboard: Optional[bool] = None
    one_time_keyboard: Optional[bool] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.rows = [KeypadRow._parse(client, row) if isinstance(row, dict) else row for row in (self.rows or [])]

    @classmethod
    def build(cls, *rows: list[Button], resize_keyboard: Optional[bool] = None, one_time_keyboard: Optional[bool] = None) -> "Keypad":
        """``Keypad.build([Button.simple("1", "A")], [Button.simple("2", "B")])``."""
        return cls(rows=[KeypadRow(buttons=list(row)) for row in rows], resize_keyboard=resize_keyboard, one_time_keyboard=one_time_keyboard)


@model
class MessageKeypadUpdate(Object):
    message_id: Optional[str] = None
    inline_keypad: Optional[Keypad] = None


__all__ = [
    "Location",
    "ButtonSelectionItem",
    "ButtonSelection",
    "ButtonCalendar",
    "ButtonNumberPicker",
    "ButtonStringPicker",
    "ButtonTextbox",
    "ButtonLocation",
    "AuxData",
    "Button",
    "KeypadRow",
    "Keypad",
    "MessageKeypadUpdate",
]
