"""The decrypted socket frame and its update kinds."""

from __future__ import annotations

from typing import Any, Optional

from .chat import ChatUpdate
from .message import MessageUpdate
from .object import Object, model


@model
class ShowActivity(Object):
    """A typing/recording/uploading indicator (``show_activities``)."""

    object_guid: Optional[str] = None
    user_guid: Optional[str] = None
    type: Optional[str] = None
    activity: Optional[str] = None
    timestamp: Optional[str] = None

    @property
    def kind(self) -> Optional[str]:
        return self.activity or self.type


@model
class NotificationMessageData(Object):
    object_guid: Optional[str] = None
    object_type: Optional[str] = None
    message_id: Optional[str] = None


@model
class ShowNotification(Object):
    notification_id: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    message_data: Optional[NotificationMessageData] = None


@model
class DraftMessage(Object):
    chat_object_guid: Optional[str] = None
    text: Optional[str] = None
    reply_to_message_id: Optional[str] = None
    time: Optional[int] = None


@model
class DraftMessageUpdate(Object):
    action: Optional[str] = None
    draft_message: Optional[DraftMessage] = None


@model
class Updates(Object):
    """Everything one decrypted ``messenger`` socket frame can carry."""

    chat_updates: list[ChatUpdate] = None  # type: ignore[assignment]
    message_updates: list[MessageUpdate] = None  # type: ignore[assignment]
    show_activities: list[ShowActivity] = None  # type: ignore[assignment]
    show_notifications: list[ShowNotification] = None  # type: ignore[assignment]
    draft_message_updates: list[DraftMessageUpdate] = None  # type: ignore[assignment]
    group_voice_chat_updates: list[Any] = None  # type: ignore[assignment]
    group_voice_chat_participant_updates: list[Any] = None  # type: ignore[assignment]
    user_guid: Optional[str] = None
    mode: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        for name in (
            "chat_updates",
            "message_updates",
            "show_activities",
            "show_notifications",
            "draft_message_updates",
            "group_voice_chat_updates",
            "group_voice_chat_participant_updates",
        ):
            if getattr(self, name) is None:
                setattr(self, name, [])

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.chat_updates,
                self.message_updates,
                self.show_activities,
                self.show_notifications,
                self.draft_message_updates,
                self.group_voice_chat_updates,
                self.group_voice_chat_participant_updates,
            )
        )

    @property
    def messages(self) -> list[Any]:
        """The message objects of every ``message_updates`` entry (with ``action`` set)."""
        return [update.message for update in self.message_updates if update.message is not None]


SocketUpdates = Updates

__all__ = [
    "DraftMessage",
    "DraftMessageUpdate",
    "NotificationMessageData",
    "ShowActivity",
    "ShowNotification",
    "SocketUpdates",
    "Updates",
]
