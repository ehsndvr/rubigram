"""Composable update filters (``&``, ``|``, ``~``) for user and bot messages."""

from __future__ import annotations

import contextlib
import inspect
import re
from typing import Any, Callable, Iterable, Optional, Pattern, Sequence

FilterFunc = Callable[[Any, Any], Any]


class Filter:
    """Wraps a sync or async ``func(client, update) -> bool``.

    Instances compose with ``&`` (and), ``|`` (or) and ``~`` (not).  Call
    ``await flt(client, update)`` to evaluate; :meth:`check_sync` evaluates
    purely synchronous filters without an event loop.
    """

    def __init__(self, func: FilterFunc, name: str = "custom"):
        self.func = func
        self.name = name

    async def __call__(self, client: Any, update: Any) -> bool:
        result = self.func(client, update)
        if inspect.isawaitable(result):
            result = await result
        return bool(result)

    def check_sync(self, client: Any, update: Any) -> bool:
        result = self.func(client, update)
        if inspect.isawaitable(result):
            close = getattr(result, "close", None)
            if close is not None:
                close()
            raise TypeError(f"filter {self.name} is asynchronous; await it instead")
        return bool(result)

    def __and__(self, other: Filter) -> Filter:
        async def func(client: Any, update: Any) -> bool:
            return await self(client, update) and await other(client, update)

        return Filter(func, f"({self.name}&{other.name})")

    def __or__(self, other: Filter) -> Filter:
        async def func(client: Any, update: Any) -> bool:
            return await self(client, update) or await other(client, update)

        return Filter(func, f"({self.name}|{other.name})")

    def __invert__(self) -> Filter:
        async def func(client: Any, update: Any) -> bool:
            return not await self(client, update)

        return Filter(func, f"~{self.name}")

    def __repr__(self) -> str:
        return f"rubigram.filters.{self.name}"


def create(func: FilterFunc, name: Optional[str] = None) -> Filter:
    """Create a filter from any callable ``(client, update) -> bool`` (sync or async)."""
    return Filter(func, name or getattr(func, "__name__", "custom"))


# ---------------------------------------------------------------------------
# helpers reading both the user-API Message and the bot Message
# ---------------------------------------------------------------------------


def _attr(update: Any, key: str, default: Any = None) -> Any:
    return getattr(update, key, default)


def _message_type(update: Any) -> Optional[str]:
    return _attr(update, "type")


def _file_type(update: Any) -> Optional[str]:
    file_inline = _attr(update, "file_inline")
    if file_inline is not None:
        return getattr(file_inline, "type", None)
    return None


def _event_type(update: Any) -> Optional[str]:
    event = _attr(update, "event_data")
    return getattr(event, "type", None) if event is not None else None


def _metadata_types(update: Any) -> set[str]:
    metadata = _attr(update, "metadata")
    parts: Iterable[Any] = ()
    if metadata is None:
        parts = ()
    elif isinstance(metadata, list):
        parts = metadata
    else:
        parts = getattr(metadata, "meta_data_parts", None) or []
    found: set[str] = set()
    for part in parts:
        part_type = getattr(part, "type", None) or (part.get("type") if isinstance(part, dict) else None)
        if part_type:
            found.add(str(getattr(part_type, "value", part_type)))
    return found


def _text(update: Any) -> str:
    return _attr(update, "text") or ""


# ---------------------------------------------------------------------------
# built-in filters
# ---------------------------------------------------------------------------

all = create(lambda client, update: True, "all")
me = create(lambda client, update: bool(_attr(update, "is_mine", False)), "me")
outgoing = me
incoming = create(lambda client, update: not _attr(update, "is_mine", False), "incoming")
private = create(lambda client, update: _attr(update, "chat_type") == "User", "private")
bot = create(lambda client, update: _attr(update, "chat_type") == "Bot", "bot")
group = create(lambda client, update: _attr(update, "chat_type") == "Group", "group")
channel = create(lambda client, update: _attr(update, "chat_type") == "Channel", "channel")
service = create(lambda client, update: _attr(update, "chat_type") == "Service", "service")

text = create(lambda client, update: _message_type(update) == "Text", "text")
poll = create(lambda client, update: _message_type(update) in {"Poll", "Poll3"}, "poll")
quiz = create(lambda client, update: _message_type(update) == "Poll3", "quiz")
rubino = create(lambda client, update: _message_type(update) == "RubinoPost", "rubino")
sticker = create(lambda client, update: _message_type(update) == "Sticker" or _attr(update, "sticker") is not None, "sticker")
live = create(lambda client, update: _message_type(update) == "Live", "live")
caption = create(lambda client, update: bool(_text(update)) and _message_type(update) == "FileInlineCaption", "caption")
event = create(lambda client, update: _message_type(update) == "Event", "event")
location = create(lambda client, update: _attr(update, "location") is not None or _message_type(update) == "Location", "location")
contact = create(lambda client, update: _attr(update, "contact_message") is not None, "contact")
media = create(
    lambda client, update: (
        _attr(update, "file_inline") is not None
        or _attr(update, "file") is not None
        or _message_type(update) in {"Sticker", "RubinoPost", "Live"}
    ),
    "media",
)
gif = create(lambda client, update: _file_type(update) == "Gif", "gif")
video = create(lambda client, update: _file_type(update) == "Video", "video")
photo = create(lambda client, update: _file_type(update) == "Image", "photo")
voice = create(lambda client, update: _file_type(update) == "Voice", "voice")
music = create(lambda client, update: _file_type(update) == "Music", "music")
document = create(
    lambda client, update: _file_type(update) == "File" or (_attr(update, "file") is not None and _file_type(update) is None), "document"
)

metadata = create(lambda client, update: bool(_metadata_types(update)), "metadata")
bold = create(lambda client, update: "Bold" in _metadata_types(update), "bold")
mono = create(lambda client, update: "Mono" in _metadata_types(update), "mono")
italic = create(lambda client, update: "Italic" in _metadata_types(update), "italic")
mention = create(lambda client, update: "Mention" in _metadata_types(update), "mention")

new = create(lambda client, update: _attr(update, "action") in (None, "New"), "new")
edited = create(lambda client, update: _attr(update, "action") == "Edit" or bool(_attr(update, "is_edited", False)), "edited")
deleted = create(lambda client, update: _attr(update, "action") == "Delete", "deleted")
replied = create(lambda client, update: _attr(update, "reply_to_message_id") is not None, "replied")
reply = replied
forwarded = create(lambda client, update: _attr(update, "forwarded_from") is not None, "forwarded")
forwarded_no_link = create(lambda client, update: bool(_attr(update, "forwarded_no_link", False)), "forwarded_no_link")
scheduled = create(lambda client, update: bool(_attr(update, "is_scheduled", False)), "scheduled")

member_added = create(lambda client, update: _event_type(update) == "AddedGroupMembers", "member_added")
member_joined = create(lambda client, update: _event_type(update) == "JoinedGroupByLink", "member_joined")
member_left = create(lambda client, update: _event_type(update) == "LeaveGroup", "member_left")
member_removed = create(lambda client, update: _event_type(update) == "RemoveGroupMembers", "member_removed")
message_pinned = create(lambda client, update: _event_type(update) == "PinnedMessageUpdated", "message_pinned")
voice_chat_started = create(lambda client, update: _event_type(update) == "VoiceChatStarted", "voice_chat_started")
voice_chat_finished = create(lambda client, update: _event_type(update) == "VoiceChatFinished", "voice_chat_finished")

# Bot API specifics
button = create(
    lambda client, update: _attr(update, "aux_data") is not None and getattr(update.aux_data, "button_id", None) is not None, "button"
)
from_bot = create(lambda client, update: str(_attr(update, "sender_type") or "") == "Bot", "from_bot")


# ---------------------------------------------------------------------------
# factories
# ---------------------------------------------------------------------------


def regex(pattern: str | Pattern[str], flags: int = 0) -> Filter:
    """Match ``message.text`` against a regular expression; stores the match as ``message.matches``."""
    compiled = re.compile(pattern, flags) if isinstance(pattern, str) else pattern

    def func(client: Any, update: Any) -> bool:
        match = compiled.search(_text(update))
        if match is None:
            return False
        with contextlib.suppress(AttributeError):  # frozen objects
            update.matches = [match]
        return True

    return create(func, f"regex:{compiled.pattern}")


def command(commands: str | Sequence[str], prefixes: str | Sequence[str] = "/", *, case_sensitive: bool = False) -> Filter:
    """Match ``/command args``; the parsed parts are stored on ``message.command``."""
    if isinstance(commands, str):
        wanted = {commands}
    else:
        wanted = set(commands)
    if not case_sensitive:
        wanted = {item.lower() for item in wanted}
    allowed_prefixes = tuple(prefixes)

    def func(client: Any, update: Any) -> bool:
        body = _text(update).strip()
        if not body or body[0] not in allowed_prefixes:
            return False
        parts = body[1:].split()
        if not parts:
            return False
        head = parts[0].split("@", 1)[0]
        name = head if case_sensitive else head.lower()
        if name not in wanted:
            return False
        update.command = [name, *parts[1:]]
        return True

    return create(func, "command:" + ",".join(sorted(wanted)))


def chat(*object_guids: str) -> Filter:
    """Messages in the given chats (``object_guid`` / bot ``chat_id``)."""
    wanted = {str(guid) for guid in object_guids}
    return create(lambda client, update: (_attr(update, "object_guid") or _attr(update, "chat_id")) in wanted, "chat")


def user(*user_guids: str) -> Filter:
    """Messages sent by the given users (``author_object_guid`` / bot ``sender_id``)."""
    wanted = {str(guid) for guid in user_guids}
    return create(lambda client, update: (_attr(update, "author_object_guid") or _attr(update, "sender_id")) in wanted, "user")


def button_id(*ids: str) -> Filter:
    """Inline-button callbacks with one of the given ``button_id`` values."""
    wanted = {str(item) for item in ids}

    def func(client: Any, update: Any) -> bool:
        aux = _attr(update, "aux_data")
        return aux is not None and getattr(aux, "button_id", None) in wanted

    return create(func, "button_id")


group_link = regex(r"rubika\.ir/joing/\w{32}")
channel_link = regex(r"rubika\.ir/joinc/\w{32}")


__all__ = [
    "Filter",
    "all",
    "bold",
    "bot",
    "button",
    "button_id",
    "caption",
    "channel",
    "channel_link",
    "chat",
    "command",
    "contact",
    "create",
    "deleted",
    "document",
    "edited",
    "event",
    "forwarded",
    "forwarded_no_link",
    "from_bot",
    "gif",
    "group",
    "group_link",
    "incoming",
    "italic",
    "live",
    "location",
    "me",
    "media",
    "member_added",
    "member_joined",
    "member_left",
    "member_removed",
    "mention",
    "message_pinned",
    "metadata",
    "mono",
    "music",
    "new",
    "outgoing",
    "photo",
    "poll",
    "private",
    "quiz",
    "regex",
    "replied",
    "reply",
    "rubino",
    "scheduled",
    "service",
    "sticker",
    "text",
    "user",
    "video",
    "voice",
    "voice_chat_finished",
    "voice_chat_started",
]
