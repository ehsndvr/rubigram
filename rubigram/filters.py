from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Pattern


FilterFunc = Callable[[Any, Any], bool]


@dataclass(frozen=True)
class Filter:
    func: FilterFunc
    name: str = "custom"

    def __call__(self, client: Any, message: Any) -> bool:
        return bool(self.func(client, message))

    def __and__(self, other: "Filter") -> "Filter":
        return Filter(lambda client, message: self(client, message) and other(client, message), f"({self.name}&{other.name})")

    def __or__(self, other: "Filter") -> "Filter":
        return Filter(lambda client, message: self(client, message) or other(client, message), f"({self.name}|{other.name})")

    def __invert__(self) -> "Filter":
        return Filter(lambda client, message: not self(client, message), f"~{self.name}")


def create(func: FilterFunc, name: str = "custom") -> Filter:
    return Filter(func, name)


def _attr(message: Any, key: str, default: Any = None) -> Any:
    return getattr(message, key, default)


def _message_type(message: Any) -> str | None:
    return _attr(message, "type")


def _file_inline_type(message: Any) -> str | None:
    file_inline = _attr(message, "file_inline")
    return getattr(file_inline, "type", None) if file_inline is not None else None


def _event_type(message: Any) -> str | None:
    event_data = _attr(message, "event_data")
    return getattr(event_data, "type", None) if event_data is not None else None


def _metadata_types(message: Any) -> set[str]:
    metadata = _attr(message, "metadata") or []
    return {getattr(item, "type", None) for item in metadata if getattr(item, "type", None)}


all = create(lambda client, message: True, "all")
me = create(lambda client, message: bool(_attr(message, "is_mine", False)), "me")
private = create(lambda client, message: _attr(message, "chat_type") == "User", "private")
bot = create(lambda client, message: _attr(message, "chat_type") == "Bot", "bot")
group = create(lambda client, message: _attr(message, "chat_type") == "Group", "group")
channel = create(lambda client, message: _attr(message, "chat_type") == "Channel", "channel")
service = create(lambda client, message: _attr(message, "chat_type") == "Service", "service")

text = create(lambda client, message: _message_type(message) == "Text", "text")
poll = create(lambda client, message: _message_type(message) == "Poll", "poll")
quiz = create(lambda client, message: _message_type(message) == "Poll3", "quiz")
rubino = create(lambda client, message: _message_type(message) == "RubinoPost", "rubino")
sticker = create(lambda client, message: _message_type(message) == "Sticker", "sticker")
live = create(lambda client, message: _message_type(message) == "Live", "live")
caption = create(lambda client, message: bool(getattr(message, "text", None)) and _message_type(message) == "FileInlineCaption", "caption")
event = create(lambda client, message: _message_type(message) == "Event", "event")
media = create(
    lambda client, message: _attr(message, "file_inline") is not None or _message_type(message) in {"Sticker", "RubinoPost", "Live"},
    "media",
)
gif = create(lambda client, message: _file_inline_type(message) == "Gif", "gif")
video = create(lambda client, message: _file_inline_type(message) == "Video", "video")
photo = create(lambda client, message: _file_inline_type(message) == "Image", "photo")
voice = create(lambda client, message: _file_inline_type(message) == "Voice", "voice")
music = create(lambda client, message: _file_inline_type(message) == "Music", "music")
document = create(lambda client, message: _file_inline_type(message) == "File", "document")

metadata = create(lambda client, message: bool(_attr(message, "metadata")), "metadata")
bold = create(lambda client, message: "Bold" in _metadata_types(message), "bold")
mono = create(lambda client, message: "Mono" in _metadata_types(message), "mono")
italic = create(lambda client, message: "Italic" in _metadata_types(message), "italic")
mention = create(lambda client, message: "Mention" in _metadata_types(message), "mention")

new = create(lambda client, message: _attr(message, "action") == "New", "new")
edited = create(lambda client, message: _attr(message, "action") == "Edit", "edited")
deleted = create(lambda client, message: _attr(message, "action") == "Delete", "deleted")
replied = create(lambda client, message: _attr(message, "reply_to_message_id") is not None, "replied")
forwarded = create(lambda client, message: _attr(message, "forwarded_from") is not None, "forwarded")
forwarded_no_link = create(lambda client, message: bool(_attr(message, "forwarded_no_link", False)), "forwarded_no_link")

member_added = create(lambda client, message: _event_type(message) == "AddedGroupMembers", "member_added")
member_joined = create(lambda client, message: _event_type(message) == "JoinedGroupByLink", "member_joined")
member_left = create(lambda client, message: _event_type(message) == "LeaveGroup", "member_left")
member_removed = create(lambda client, message: _event_type(message) == "RemoveGroupMembers", "member_removed")
message_pinned = create(lambda client, message: _event_type(message) == "PinnedMessageUpdated", "message_pinned")
voice_chat_started = create(lambda client, message: _event_type(message) == "VoiceChatStarted", "voice_chat_started")
voice_chat_finished = create(lambda client, message: _event_type(message) == "VoiceChatFinished", "voice_chat_finished")


def regex(pattern: str | Pattern[str]) -> Filter:
    compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
    return create(lambda client, message: bool(compiled.search(getattr(message, "text", "") or "")), f"regex:{compiled.pattern}")


group_link = regex(r"rubika\.ir/joing/\w{32}")
channel_link = regex(r"rubika\.ir/joinc/\w{32}")
