"""Settings, privacy, two-step verification, sessions and folders."""

from __future__ import annotations

from typing import Any, Optional

from .object import Object, model


@model
class PrivacySetting(Object):
    show_my_phone_number: Optional[str] = None
    show_my_last_online: Optional[str] = None
    show_my_profile_photo: Optional[str] = None
    link_forward_message: Optional[str] = None
    can_join_chat_by: Optional[str] = None
    show_my_bio: Optional[str] = None
    can_be_called_by: Optional[str] = None


@model
class PrivacySettingResult(Object):
    privacy_setting: Optional[PrivacySetting] = None
    timestamp: Optional[str] = None


@model
class NotificationSetting(Object):
    new_chat: Optional[bool] = None
    private_chat: Optional[bool] = None
    group_chat: Optional[bool] = None
    channel: Optional[bool] = None
    in_app_sound: Optional[bool] = None
    in_app_vibrate: Optional[bool] = None
    in_app_preview: Optional[bool] = None
    in_chat_sound: Optional[bool] = None
    contact_joined: Optional[bool] = None
    pinned_messages: Optional[bool] = None


@model
class UserSetting(Object):
    privacy_setting: Optional[PrivacySetting] = None
    notification_setting: Optional[NotificationSetting] = None
    show_my_last_online: Optional[str] = None
    show_my_phone_number: Optional[str] = None
    show_my_profile_photo: Optional[str] = None
    link_forward_message: Optional[str] = None
    can_join_chat_by: Optional[str] = None


@model
class UserSettingResult(Object):
    setting: Optional[UserSetting] = None
    user_setting: Optional[UserSetting] = None
    timestamp: Optional[str] = None

    @property
    def settings(self) -> Optional[UserSetting]:
        return self.setting or self.user_setting


@model
class TwoStepStatus(Object):
    is_two_step_verification_on: Optional[bool] = None
    has_recovery_email: Optional[bool] = None
    has_confirmed_recovery_email: Optional[bool] = None
    has_pending_recovery_email: Optional[bool] = None
    pending_recovery_email: Optional[str] = None
    recovery_email: Optional[str] = None
    hint: Optional[str] = None
    password_hint: Optional[str] = None
    sign_in_type: Optional[str] = None


@model
class TwoStepStatusResult(Object):
    two_step_status: Optional[TwoStepStatus] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None


@model
class SessionInfo(Object):
    key: Optional[str] = None
    session_key: Optional[str] = None
    app_name: Optional[str] = None
    app_version: Optional[str] = None
    platform: Optional[str] = None
    device_model: Optional[str] = None
    system_version: Optional[str] = None
    ip: Optional[str] = None
    location: Optional[str] = None
    last_online: Optional[int] = None
    create_time: Optional[int] = None
    is_current: Optional[bool] = None


@model
class MySessions(Object):
    sessions: list[SessionInfo] = None  # type: ignore[assignment]
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.sessions = self.sessions or []

    def __iter__(self):
        return iter(self.sessions)

    def __len__(self) -> int:
        return len(self.sessions)


@model
class UnconfirmedSession(Object):
    unconfirmed_session_key: Optional[str] = None
    app_name: Optional[str] = None
    platform: Optional[str] = None
    device_model: Optional[str] = None
    ip: Optional[str] = None
    location: Optional[str] = None
    create_time: Optional[int] = None


@model
class UnconfirmedSessions(Object):
    unconfirmed_sessions: list[UnconfirmedSession] = None  # type: ignore[assignment]

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.unconfirmed_sessions = self.unconfirmed_sessions or []


@model
class Folder(Object):
    folder_id: Optional[str] = None
    name: Optional[str] = None
    include_chat_types: list[str] = None  # type: ignore[assignment]
    exclude_chat_types: list[str] = None  # type: ignore[assignment]
    include_object_guids: list[str] = None  # type: ignore[assignment]
    exclude_object_guids: list[str] = None  # type: ignore[assignment]
    pinned_object_guids: list[str] = None  # type: ignore[assignment]
    is_add_to_top: Optional[bool] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        for name in ("include_chat_types", "exclude_chat_types", "include_object_guids", "exclude_object_guids", "pinned_object_guids"):
            if getattr(self, name) is None:
                setattr(self, name, [])


@model
class FoldersResult(Object):
    folders: list[Folder] = None  # type: ignore[assignment]
    suggested_folders: list[Folder] = None  # type: ignore[assignment]
    new_state: Optional[int] = None
    old_state: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self, client: Any = None) -> None:
        super().__post_init__(client)
        self.folders = self.folders or []
        self.suggested_folders = self.suggested_folders or []


@model
class FolderResult(Object):
    folder: Optional[Folder] = None
    new_state: Optional[int] = None
    old_state: Optional[int] = None
    timestamp: Optional[str] = None


@model
class ChangePhoneRequest(Object):
    phone_code_hash: Optional[str] = None
    hash: Optional[str] = None
    status: Optional[str] = None
    code_digits_count: Optional[int] = None
    send_type: Optional[str] = None


__all__ = [
    "ChangePhoneRequest",
    "Folder",
    "FolderResult",
    "FoldersResult",
    "MySessions",
    "NotificationSetting",
    "PrivacySetting",
    "PrivacySettingResult",
    "SessionInfo",
    "TwoStepStatus",
    "TwoStepStatusResult",
    "UnconfirmedSession",
    "UnconfirmedSessions",
    "UserSetting",
    "UserSettingResult",
]
