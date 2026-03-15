from __future__ import annotations

from typing import Any, Iterable, Optional

from .object import Object


def _parse_dynamic(client: Any, value: Any) -> Any:
    if isinstance(value, dict):
        return RawObject._parse(client, value)
    if isinstance(value, list):
        return [_parse_dynamic(client, item) for item in value]
    return value


def _apply_unknown_fields(target: Object, client: Any, data: dict[str, Any], known_fields: Iterable[str]) -> None:
    known = set(known_fields)
    for key, value in data.items():
        if key not in known:
            setattr(target, key, _parse_dynamic(client, value))


class RawObject(Object):
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
            return [_parse_dynamic(client, item) for item in data]
        if not isinstance(data, dict):
            return data
        return cls(client=client, **{key: _parse_dynamic(client, value) for key, value in data.items()})


class Empty(RawObject):
    pass


class OnlineTime(RawObject):
    pass


class User(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        user_guid: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        username: Optional[str] = None,
        last_online: Optional[int] = None,
        is_deleted: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        online_time: Optional[OnlineTime] = None,
    ):
        super().__init__(client)
        self.user_guid = user_guid
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.username = username
        self.last_online = last_online
        self.is_deleted = is_deleted
        self.is_verified = is_verified
        self.online_time = online_time

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["User"]:
        if data is None:
            return None
        result = cls(
            client=client,
            user_guid=data.get("user_guid"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone=data.get("phone"),
            username=data.get("username"),
            last_online=data.get("last_online"),
            is_deleted=data.get("is_deleted"),
            is_verified=data.get("is_verified"),
            online_time=OnlineTime._parse(client, data.get("online_time")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class Message(RawObject):
    pass


class PeerObject(RawObject):
    pass


class UserAdditionalInfo(RawObject):
    pass


class Chat(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        object_guid: Optional[str] = None,
        access: Optional[list[str]] = None,
        count_unseen: Optional[int] = None,
        is_mute: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
        time_string: Optional[str] = None,
        last_message: Optional[Message] = None,
        last_seen_my_mid: Optional[str] = None,
        last_seen_peer_mid: Optional[str] = None,
        status: Optional[str] = None,
        time: Optional[int] = None,
        abs_object: Optional[PeerObject] = None,
        is_blocked: Optional[bool] = None,
        last_message_id: Optional[str] = None,
        last_deleted_mid: Optional[str] = None,
        is_in_contact: Optional[bool] = None,
        show_ask_spam: Optional[bool] = None,
        auto_delete: Optional[str] = None,
    ):
        super().__init__(client)
        self.object_guid = object_guid
        self.access = access
        self.count_unseen = count_unseen
        self.is_mute = is_mute
        self.is_pinned = is_pinned
        self.time_string = time_string
        self.last_message = last_message
        self.last_seen_my_mid = last_seen_my_mid
        self.last_seen_peer_mid = last_seen_peer_mid
        self.status = status
        self.time = time
        self.abs_object = abs_object
        self.is_blocked = is_blocked
        self.last_message_id = last_message_id
        self.last_deleted_mid = last_deleted_mid
        self.is_in_contact = is_in_contact
        self.show_ask_spam = show_ask_spam
        self.auto_delete = auto_delete

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Chat"]:
        if data is None:
            return None
        result = cls(
            client=client,
            object_guid=data.get("object_guid"),
            access=data.get("access"),
            count_unseen=data.get("count_unseen"),
            is_mute=data.get("is_mute"),
            is_pinned=data.get("is_pinned"),
            time_string=data.get("time_string"),
            last_message=Message._parse(client, data.get("last_message")),
            last_seen_my_mid=data.get("last_seen_my_mid"),
            last_seen_peer_mid=data.get("last_seen_peer_mid"),
            status=data.get("status"),
            time=data.get("time"),
            abs_object=PeerObject._parse(client, data.get("abs_object")),
            is_blocked=data.get("is_blocked"),
            last_message_id=data.get("last_message_id"),
            last_deleted_mid=data.get("last_deleted_mid"),
            is_in_contact=data.get("is_in_contact"),
            show_ask_spam=data.get("show_ask_spam"),
            auto_delete=data.get("auto_delete"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class SentCode(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        phone_code_hash: Optional[str] = None,
        status: Optional[str] = None,
        code_digits_count: Optional[int] = None,
        has_confirmed_recovery_email: Optional[bool] = None,
        no_recovery_alert: Optional[str] = None,
        send_type: Optional[str] = None,
    ):
        super().__init__(client)
        self.phone_code_hash = phone_code_hash
        self.status = status
        self.code_digits_count = code_digits_count
        self.has_confirmed_recovery_email = has_confirmed_recovery_email
        self.no_recovery_alert = no_recovery_alert
        self.send_type = send_type

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SentCode"]:
        if data is None:
            return None
        result = cls(
            client=client,
            phone_code_hash=data.get("phone_code_hash"),
            status=data.get("status"),
            code_digits_count=data.get("code_digits_count"),
            has_confirmed_recovery_email=data.get("has_confirmed_recovery_email"),
            no_recovery_alert=data.get("no_recovery_alert"),
            send_type=data.get("send_type"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class Authorization(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        status: Optional[str] = None,
        auth: Optional[str] = None,
        user: Optional[User] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.status = status
        self.auth = auth
        self.user = user
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Authorization"]:
        if data is None:
            return None
        result = cls(
            client=client,
            status=data.get("status"),
            auth=data.get("auth"),
            user=User._parse(client, data.get("user")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class UserInfo(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        user: Optional[User] = None,
        chat: Optional[Chat] = None,
        timestamp: Optional[str] = None,
        is_in_contact: Optional[bool] = None,
        can_receive_call: Optional[bool] = None,
        can_video_call: Optional[bool] = None,
        user_additional_info: Optional[UserAdditionalInfo] = None,
    ):
        super().__init__(client)
        self.user = user
        self.chat = chat
        self.timestamp = timestamp
        self.is_in_contact = is_in_contact
        self.can_receive_call = can_receive_call
        self.can_video_call = can_video_call
        self.user_additional_info = user_additional_info

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["UserInfo"]:
        if data is None:
            return None
        result = cls(
            client=client,
            user=User._parse(client, data.get("user")),
            chat=Chat._parse(client, data.get("chat")),
            timestamp=data.get("timestamp"),
            is_in_contact=data.get("is_in_contact"),
            can_receive_call=data.get("can_receive_call"),
            can_video_call=data.get("can_video_call"),
            user_additional_info=UserAdditionalInfo._parse(client, data.get("user_additional_info")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ObjectByUsername(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        exist: Optional[bool] = None,
        type: Optional[str] = None,
        user: Optional[User] = None,
        chat: Optional[Chat] = None,
        timestamp: Optional[str] = None,
        is_in_contact: Optional[bool] = None,
    ):
        super().__init__(client)
        self.exist = exist
        self.type = type
        self.user = user
        self.chat = chat
        self.timestamp = timestamp
        self.is_in_contact = is_in_contact

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ObjectByUsername"]:
        if data is None:
            return None
        result = cls(
            client=client,
            exist=data.get("exist"),
            type=data.get("type"),
            user=User._parse(client, data.get("user")),
            chat=Chat._parse(client, data.get("chat")),
            timestamp=data.get("timestamp"),
            is_in_contact=data.get("is_in_contact"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class AvatarFile(RawObject):
    pass


class Avatar(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        avatar_id: Optional[str] = None,
        thumbnail: Optional[AvatarFile] = None,
        main: Optional[AvatarFile] = None,
        create_time: Optional[int] = None,
    ):
        super().__init__(client)
        self.avatar_id = avatar_id
        self.thumbnail = thumbnail
        self.main = main
        self.create_time = create_time

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Avatar"]:
        if data is None:
            return None
        result = cls(
            client=client,
            avatar_id=data.get("avatar_id"),
            thumbnail=AvatarFile._parse(client, data.get("thumbnail")),
            main=AvatarFile._parse(client, data.get("main")),
            create_time=data.get("create_time"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ChatAvatars(Object):
    def __init__(self, *, client: Any = None, avatars: Optional[list[Avatar]] = None):
        super().__init__(client)
        self.avatars = avatars or []

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ChatAvatars"]:
        if data is None:
            return None
        result = cls(
            client=client,
            avatars=[Avatar._parse(client, avatar) for avatar in data.get("avatars", [])],
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class MessageUpdate(RawObject):
    pass


class ChatUpdate(RawObject):
    pass


class SentMessage(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        message_update: Optional[MessageUpdate] = None,
        status: Optional[str] = None,
        chat_update: Optional[ChatUpdate] = None,
    ):
        super().__init__(client)
        self.message_update = message_update
        self.status = status
        self.chat_update = chat_update

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SentMessage"]:
        if data is None:
            return None
        result = cls(
            client=client,
            message_update=MessageUpdate._parse(client, data.get("message_update")),
            status=data.get("status"),
            chat_update=ChatUpdate._parse(client, data.get("chat_update")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result
