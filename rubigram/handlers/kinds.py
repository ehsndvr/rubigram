"""Concrete handler classes, one per update kind."""

from __future__ import annotations

from .handler import Handler


class MessageHandler(Handler):
    """New messages (user API ``action == "New"``; bot ``NewMessage``)."""

    kind = "message"


class EditedMessageHandler(Handler):
    """Edited messages (``action == "Edit"``; bot ``UpdatedMessage``)."""

    kind = "edited_message"


class DeletedMessageHandler(Handler):
    """Deleted messages (``action == "Delete"``; bot ``RemovedMessage``)."""

    kind = "deleted_message"


class ChatUpdateHandler(Handler):
    """``chat_updates`` entries (unread counts, pins, new chats …)."""

    kind = "chat_update"


class ActivityHandler(Handler):
    """``show_activities`` entries (typing, recording, uploading)."""

    kind = "activity"


class NotificationHandler(Handler):
    """``show_notifications`` entries."""

    kind = "notification"


class DraftUpdateHandler(Handler):
    kind = "draft_update"


class InlineMessageHandler(Handler):
    """Bot inline messages (button interactions delivered by webhooks)."""

    kind = "inline_message"


class CallbackQueryHandler(Handler):
    """Bot button presses (``inline_message``/``new_message`` carrying ``aux_data.button_id``)."""

    kind = "callback_query"


class RawUpdateHandler(Handler):
    """Every decrypted socket frame (:class:`~rubigram.types.Updates`) or bot update."""

    kind = "raw"


__all__ = [
    "MessageHandler",
    "EditedMessageHandler",
    "DeletedMessageHandler",
    "ChatUpdateHandler",
    "ActivityHandler",
    "NotificationHandler",
    "DraftUpdateHandler",
    "InlineMessageHandler",
    "CallbackQueryHandler",
    "RawUpdateHandler",
]
