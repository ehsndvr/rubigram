from __future__ import annotations

import time
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


async def _download_bound_file(
    target: Object,
    *,
    path: str | None = None,
    in_memory: bool = False,
    file_name: Optional[str] = None,
    progress: Any = None,
    progress_args: tuple[Any, ...] = (),
    missing_message: str,
) -> Any:
    if target._client is None:
        raise RuntimeError(missing_message)
    return await target._client.download_file(
        target,
        path=path,
        in_memory=in_memory,
        file_name=file_name,
        progress=progress,
        progress_args=progress_args,
    )


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


class UploadDescriptor(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        id: Optional[str] = None,
        dc_id: Optional[str] = None,
        access_hash_send: Optional[str] = None,
        access_hash_rec: Optional[str] = None,
        upload_url: Optional[str] = None,
    ):
        super().__init__(client)
        self.id = id
        self.dc_id = dc_id
        self.access_hash_send = access_hash_send
        self.access_hash_rec = access_hash_rec
        self.upload_url = upload_url

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["UploadDescriptor"]:
        if data is None:
            return None
        result = cls(
            client=client,
            id=data.get("id"),
            dc_id=data.get("dc_id"),
            access_hash_send=data.get("access_hash_send"),
            access_hash_rec=data.get("access_hash_rec"),
            upload_url=data.get("upload_url"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class OnlineTime(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        type: Optional[str] = None,
        approximate_period: Optional[str] = None,
        exact_time: Optional[int] = None,
    ):
        super().__init__(client)
        self.type = type
        self.approximate_period = approximate_period
        self.exact_time = exact_time

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["OnlineTime"]:
        if data is None:
            return None
        result = cls(
            client=client,
            type=data.get("type"),
            approximate_period=data.get("approximate_period"),
            exact_time=data.get("exact_time"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class DownloadableFile(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        file_id: Optional[str] = None,
        mime: Optional[str] = None,
        dc_id: Optional[str] = None,
        access_hash_rec: Optional[str] = None,
        file_name: Optional[str] = None,
        size: Optional[int] = None,
    ):
        super().__init__(client)
        self.file_id = file_id
        self.mime = mime
        self.dc_id = dc_id
        self.access_hash_rec = access_hash_rec
        self.file_name = file_name
        self.size = size

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["DownloadableFile"]:
        if data is None:
            return None
        result = cls(
            client=client,
            file_id=data.get("file_id"),
            mime=data.get("mime"),
            dc_id=data.get("dc_id"),
            access_hash_rec=data.get("access_hash_rec"),
            file_name=data.get("file_name"),
            size=data.get("size"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result

    async def download(
        self,
        path: str | None = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        return await _download_bound_file(
            self,
            path=path,
            in_memory=in_memory,
            file_name=file_name,
            progress=progress,
            progress_args=progress_args,
            missing_message="This file is not bound to a Client instance",
        )


class ForwardedFrom(RawObject):
    pass


class FileInline(DownloadableFile):
    pass


class StickerFile(DownloadableFile):
    pass


class Sticker(RawObject):
    @classmethod
    def _parse(cls, client: Any, data: Any) -> Any:
        result = super()._parse(client, data)
        if result is not None and getattr(result, "file", None) is not None:
            result.file = StickerFile._parse(client, result.file)
        return result

    async def download(
        self,
        path: str | None = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        if getattr(self, "file", None) is None:
            raise RuntimeError("This sticker does not contain a downloadable file")
        return await self.file.download(
            path=path,
            in_memory=in_memory,
            file_name=file_name,
            progress=progress,
            progress_args=progress_args,
        )


class RubinoPostData(RawObject):
    pass


class LiveStatus(RawObject):
    pass


class LiveData(RawObject):
    @classmethod
    def _parse(cls, client: Any, data: Any) -> Any:
        result = super()._parse(client, data)
        if result is not None and getattr(result, "live_status", None) is not None:
            result.live_status = LiveStatus._parse(client, result.live_status)
        return result


class AvatarThumbnail(DownloadableFile):
    async def download(
        self,
        path: str | None = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        return await _download_bound_file(
            self,
            path=path,
            in_memory=in_memory,
            file_name=file_name,
            progress=progress,
            progress_args=progress_args,
            missing_message="This avatar is not bound to a Client instance",
        )


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
        avatar_thumbnail: Optional[AvatarThumbnail] = None,
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
        self.avatar_thumbnail = avatar_thumbnail

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
            avatar_thumbnail=AvatarThumbnail._parse(client, data.get("avatar_thumbnail")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class Message(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        message_id: Optional[str] = None,
        type: Optional[str] = None,
        text: Optional[str] = None,
        author_object_guid: Optional[str] = None,
        is_mine: Optional[bool] = None,
        author_type: Optional[str] = None,
        object_guid: Optional[str] = None,
        forwarded_from: Optional[ForwardedFrom] = None,
        file_inline: Optional[FileInline] = None,
        sticker: Optional[Sticker] = None,
        rubino_post_data: Optional[RubinoPostData] = None,
        live_data: Optional[LiveData] = None,
    ):
        super().__init__(client)
        self.message_id = message_id
        self.type = type
        self.text = text
        self.author_object_guid = author_object_guid
        self.is_mine = is_mine
        self.author_type = author_type
        self.object_guid = object_guid
        self.forwarded_from = forwarded_from
        self.file_inline = file_inline
        self.sticker = sticker
        self.rubino_post_data = rubino_post_data
        self.live_data = live_data

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Message"]:
        if data is None:
            return None
        result = cls(
            client=client,
            message_id=data.get("message_id"),
            type=data.get("type"),
            text=data.get("text"),
            author_object_guid=data.get("author_object_guid"),
            is_mine=data.get("is_mine"),
            author_type=data.get("author_type"),
            object_guid=data.get("object_guid"),
            forwarded_from=ForwardedFrom._parse(client, data.get("forwarded_from")),
            file_inline=FileInline._parse(client, data.get("file_inline")),
            sticker=Sticker._parse(client, data.get("sticker")),
            rubino_post_data=RubinoPostData._parse(client, data.get("rubino_post_data")),
            live_data=LiveData._parse(client, data.get("live_data")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result

    async def reply(
        self,
        text: str,
        parse_mode: Optional[str] = None,
        entities: Optional[list[Any]] = None,
    ) -> Any:
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")

        object_guid = getattr(self, "object_guid", None)
        message_id = getattr(self, "message_id", None)

        if not object_guid:
            raise RuntimeError("This message does not have object_guid required for reply()")
        if not message_id:
            raise RuntimeError("This message does not have message_id required for reply()")

        return await self._client.send_message(
            object_guid=object_guid,
            rnd=str(time.time_ns()),
            text=text,
            parse_mode=parse_mode,
            entities=entities,
            reply_to_message_id=message_id,
        )

    async def download(
        self,
        path: str | None = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        if self._client is None:
            raise RuntimeError("This message is not bound to a Client instance")
        return await self._client.download_file(
            self,
            path=path,
            in_memory=in_memory,
            file_name=file_name,
            progress=progress,
            progress_args=progress_args,
        )

    @property
    def chat_id(self) -> Any:
        return getattr(self, "object_guid", None)


class PeerObject(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        object_guid: Optional[str] = None,
        type: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        avatar_thumbnail: Optional[AvatarThumbnail] = None,
        is_verified: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
    ):
        super().__init__(client)
        self.object_guid = object_guid
        self.type = type
        self.first_name = first_name
        self.last_name = last_name
        self.avatar_thumbnail = avatar_thumbnail
        self.is_verified = is_verified
        self.is_deleted = is_deleted

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["PeerObject"]:
        if data is None:
            return None
        result = cls(
            client=client,
            object_guid=data.get("object_guid"),
            type=data.get("type"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            avatar_thumbnail=AvatarThumbnail._parse(client, data.get("avatar_thumbnail")),
            is_verified=data.get("is_verified"),
            is_deleted=data.get("is_deleted"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class UserAdditionalInfo(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        is_in_contact: Optional[bool] = None,
        can_receive_call: Optional[bool] = None,
        can_video_call: Optional[bool] = None,
        registration_time: Optional[int] = None,
        country_code: Optional[str] = None,
        official_info_text: Optional[str] = None,
    ):
        super().__init__(client)
        self.is_in_contact = is_in_contact
        self.can_receive_call = can_receive_call
        self.can_video_call = can_video_call
        self.registration_time = registration_time
        self.country_code = country_code
        self.official_info_text = official_info_text

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["UserAdditionalInfo"]:
        if data is None:
            return None
        result = cls(
            client=client,
            is_in_contact=data.get("is_in_contact"),
            can_receive_call=data.get("can_receive_call"),
            can_video_call=data.get("can_video_call"),
            registration_time=data.get("registration_time"),
            country_code=data.get("country_code"),
            official_info_text=data.get("official_info_text"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


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
        avatar_thumbnail: Optional[AvatarThumbnail] = None,
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
        self.avatar_thumbnail = avatar_thumbnail
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
            avatar_thumbnail=AvatarThumbnail._parse(client, data.get("avatar_thumbnail")),
            abs_object=PeerObject._parse(client, data.get("abs_object")),
            is_blocked=data.get("is_blocked"),
            last_message_id=data.get("last_message_id"),
            last_deleted_mid=data.get("last_deleted_mid"),
            is_in_contact=data.get("is_in_contact"),
            show_ask_spam=data.get("show_ask_spam"),
            auto_delete=data.get("auto_delete"),
        )
        if result.last_message is not None and getattr(result.last_message, "object_guid", None) is None:
            setattr(result.last_message, "object_guid", result.object_guid)
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


class ContactsLastOnline(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        users: Optional[list[User]] = None,
    ):
        super().__init__(client)
        self.users = users or []

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ContactsLastOnline"]:
        if data is None:
            return None
        result = cls(
            client=client,
            users=[User._parse(client, user) for user in data.get("users", [])],
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ContactsUpdates(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        users: Optional[list[User]] = None,
        deleted_users: Optional[list[str]] = None,
        new_state: Optional[int] = None,
        status: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.users = users or []
        self.deleted_users = deleted_users or []
        self.new_state = new_state
        self.status = status
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ContactsUpdates"]:
        if data is None:
            return None
        result = cls(
            client=client,
            users=[User._parse(client, user) for user in data.get("users", [])],
            deleted_users=data.get("deleted_users") or [],
            new_state=data.get("new_state"),
            status=data.get("status"),
            timestamp=data.get("timestamp"),
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


class AvatarFile(DownloadableFile):
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


class SearchGlobalObject(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        object_guid: Optional[str] = None,
        type: Optional[str] = None,
        title: Optional[str] = None,
        avatar_thumbnail: Optional[AvatarThumbnail] = None,
        is_verified: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
        count_members: Optional[int] = None,
        username: Optional[str] = None,
        track_id: Optional[str] = None,
    ):
        super().__init__(client)
        self.object_guid = object_guid
        self.type = type
        self.title = title
        self.avatar_thumbnail = avatar_thumbnail
        self.is_verified = is_verified
        self.is_deleted = is_deleted
        self.count_members = count_members
        self.username = username
        self.track_id = track_id

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SearchGlobalObject"]:
        if data is None:
            return None
        result = cls(
            client=client,
            object_guid=data.get("object_guid"),
            type=data.get("type"),
            title=data.get("title"),
            avatar_thumbnail=AvatarThumbnail._parse(client, data.get("avatar_thumbnail")),
            is_verified=data.get("is_verified"),
            is_deleted=data.get("is_deleted"),
            count_members=data.get("count_members"),
            username=data.get("username"),
            track_id=data.get("track_id"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class SearchGlobalObjectsResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        objects: Optional[list[SearchGlobalObject]] = None,
        has_continue: Optional[bool] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.objects = objects or []
        self.has_continue = has_continue
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SearchGlobalObjectsResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            objects=[SearchGlobalObject._parse(client, item) for item in data.get("objects", [])],
            has_continue=data.get("has_continue"),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result

    def _select_download_file(self, *, use_thumbnail: bool = False) -> AvatarFile:
        file = self.thumbnail if use_thumbnail else self.main
        if file is None:
            file = self.main or self.thumbnail
        if file is None:
            raise RuntimeError("This avatar does not contain downloadable file metadata")
        return file

    def _default_download_name(self, *, use_thumbnail: bool = False, index: Optional[int] = None) -> str:
        target = self._select_download_file(use_thumbnail=use_thumbnail)
        role = "thumbnail" if use_thumbnail else "main"
        extension = (target.mime or "bin").lstrip(".")
        base = self.avatar_id or f"avatar_{index or 0}"
        return f"{base}_{role}.{extension}"

    async def download(
        self,
        path: str | None = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
        use_thumbnail: bool = False,
    ) -> Any:
        file = self._select_download_file(use_thumbnail=use_thumbnail)
        return await file.download(
            path=path,
            in_memory=in_memory,
            file_name=file_name or self._default_download_name(use_thumbnail=use_thumbnail),
            progress=progress,
            progress_args=progress_args,
        )


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

    def __iter__(self):
        return iter(self.avatars)

    def __len__(self) -> int:
        return len(self.avatars)

    def __getitem__(self, index: int) -> Avatar:
        return self.avatars[index]

    async def download(
        self,
        path: str | None = None,
        *,
        in_memory: bool = False,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
        use_thumbnail: bool = False,
    ) -> list[Any]:
        results = []
        for index, avatar in enumerate(self.avatars, start=1):
            results.append(
                await avatar.download(
                    path=path,
                    in_memory=in_memory,
                    file_name=avatar._default_download_name(use_thumbnail=use_thumbnail, index=index),
                    progress=progress,
                    progress_args=progress_args,
                    use_thumbnail=use_thumbnail,
                )
            )
        return results


class ChatReactionSetting(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        reaction_type: Optional[str] = None,
        selected_reactions: Optional[list[str]] = None,
    ):
        super().__init__(client)
        self.reaction_type = reaction_type
        self.selected_reactions = selected_reactions or []

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ChatReactionSetting"]:
        if data is None:
            return None
        result = cls(
            client=client,
            reaction_type=data.get("reaction_type"),
            selected_reactions=data.get("selected_reactions") or [],
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class AvailableReaction(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        reaction_id: Optional[str] = None,
        emoji_char: Optional[str] = None,
        name: Optional[str] = None,
    ):
        super().__init__(client)
        self.reaction_id = reaction_id
        self.emoji_char = emoji_char
        self.name = name

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["AvailableReaction"]:
        if data is None:
            return None
        result = cls(
            client=client,
            reaction_id=data.get("reaction_id"),
            emoji_char=data.get("emoji_char"),
            name=data.get("name"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class AvailableReactions(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        reactions: Optional[list[AvailableReaction]] = None,
    ):
        super().__init__(client)
        self.reactions = reactions or []

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["AvailableReactions"]:
        if data is None:
            return None
        result = cls(
            client=client,
            reactions=[AvailableReaction._parse(client, item) for item in data.get("reactions", [])],
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class Group(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        group_guid: Optional[str] = None,
        group_title: Optional[str] = None,
        count_members: Optional[int] = None,
        is_deleted: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        slow_mode: Optional[int] = None,
        chat_history_for_new_members: Optional[str] = None,
        event_messages: Optional[bool] = None,
        chat_reaction_setting: Optional[ChatReactionSetting] = None,
        is_restricted_content: Optional[bool] = None,
    ):
        super().__init__(client)
        self.group_guid = group_guid
        self.group_title = group_title
        self.count_members = count_members
        self.is_deleted = is_deleted
        self.is_verified = is_verified
        self.slow_mode = slow_mode
        self.chat_history_for_new_members = chat_history_for_new_members
        self.event_messages = event_messages
        self.chat_reaction_setting = chat_reaction_setting
        self.is_restricted_content = is_restricted_content

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Group"]:
        if data is None:
            return None
        result = cls(
            client=client,
            group_guid=data.get("group_guid"),
            group_title=data.get("group_title"),
            count_members=data.get("count_members"),
            is_deleted=data.get("is_deleted"),
            is_verified=data.get("is_verified"),
            slow_mode=data.get("slow_mode"),
            chat_history_for_new_members=data.get("chat_history_for_new_members"),
            event_messages=data.get("event_messages"),
            chat_reaction_setting=ChatReactionSetting._parse(client, data.get("chat_reaction_setting")),
            is_restricted_content=data.get("is_restricted_content"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class Channel(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        channel_guid: Optional[str] = None,
        channel_title: Optional[str] = None,
        avatar_thumbnail: Optional[AvatarThumbnail] = None,
        count_members: Optional[int] = None,
        description: Optional[str] = None,
        is_deleted: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        channel_type: Optional[str] = None,
        sign_messages: Optional[bool] = None,
        chat_reaction_setting: Optional[ChatReactionSetting] = None,
        is_restricted_content: Optional[bool] = None,
    ):
        super().__init__(client)
        self.channel_guid = channel_guid
        self.channel_title = channel_title
        self.avatar_thumbnail = avatar_thumbnail
        self.count_members = count_members
        self.description = description
        self.is_deleted = is_deleted
        self.is_verified = is_verified
        self.channel_type = channel_type
        self.sign_messages = sign_messages
        self.chat_reaction_setting = chat_reaction_setting
        self.is_restricted_content = is_restricted_content

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["Channel"]:
        if data is None:
            return None
        result = cls(
            client=client,
            channel_guid=data.get("channel_guid"),
            channel_title=data.get("channel_title"),
            avatar_thumbnail=AvatarThumbnail._parse(client, data.get("avatar_thumbnail")),
            count_members=data.get("count_members"),
            description=data.get("description"),
            is_deleted=data.get("is_deleted"),
            is_verified=data.get("is_verified"),
            channel_type=data.get("channel_type"),
            sign_messages=data.get("sign_messages"),
            chat_reaction_setting=ChatReactionSetting._parse(client, data.get("chat_reaction_setting")),
            is_restricted_content=data.get("is_restricted_content"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class GroupMember(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        member_type: Optional[str] = None,
        member_guid: Optional[str] = None,
        title: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        is_verified: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
        last_online: Optional[int] = None,
        join_type: Optional[str] = None,
        online_time: Optional[OnlineTime] = None,
    ):
        super().__init__(client)
        self.member_type = member_type
        self.member_guid = member_guid
        self.title = title
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.is_verified = is_verified
        self.is_deleted = is_deleted
        self.last_online = last_online
        self.join_type = join_type
        self.online_time = online_time

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["GroupMember"]:
        if data is None:
            return None
        result = cls(
            client=client,
            member_type=data.get("member_type"),
            member_guid=data.get("member_guid"),
            title=data.get("title"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            username=data.get("username"),
            is_verified=data.get("is_verified"),
            is_deleted=data.get("is_deleted"),
            last_online=data.get("last_online"),
            join_type=data.get("join_type"),
            online_time=OnlineTime._parse(client, data.get("online_time")),
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


class DeleteChatHistoryResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        chat_update: Optional[SocketChatUpdate] = None,
    ):
        super().__init__(client)
        self.chat_update = chat_update

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["DeleteChatHistoryResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            chat_update=SocketChatUpdate._parse(client, data.get("chat_update")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class AddGroupResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        group: Optional[Group] = None,
        chat_update: Optional[SocketChatUpdate] = None,
        message_update: Optional[SocketMessageUpdate] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.group = group
        self.chat_update = chat_update
        self.message_update = message_update
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["AddGroupResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            group=Group._parse(client, data.get("group")),
            chat_update=SocketChatUpdate._parse(client, data.get("chat_update")),
            message_update=SocketMessageUpdate._parse(client, data.get("message_update")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class AddChannelResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        channel: Optional[Channel] = None,
        chat_update: Optional[SocketChatUpdate] = None,
        message_update: Optional[SocketMessageUpdate] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.channel = channel
        self.chat_update = chat_update
        self.message_update = message_update
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["AddChannelResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            channel=Channel._parse(client, data.get("channel")),
            chat_update=SocketChatUpdate._parse(client, data.get("chat_update")),
            message_update=SocketMessageUpdate._parse(client, data.get("message_update")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class AddChannelMembersResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        added_in_chat_members: Optional[list[GroupMember]] = None,
        timestamp: Optional[str] = None,
        channel: Optional[Channel] = None,
    ):
        super().__init__(client)
        self.added_in_chat_members = added_in_chat_members or []
        self.timestamp = timestamp
        self.channel = channel

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["AddChannelMembersResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            added_in_chat_members=[GroupMember._parse(client, item) for item in data.get("added_in_chat_members", [])],
            timestamp=data.get("timestamp"),
            channel=Channel._parse(client, data.get("channel")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class EditChannelInfoResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        channel: Optional[Channel] = None,
        chat_update: Optional[SocketChatUpdate] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.channel = channel
        self.chat_update = chat_update
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["EditChannelInfoResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            channel=Channel._parse(client, data.get("channel")),
            chat_update=SocketChatUpdate._parse(client, data.get("chat_update")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class EditGroupInfoResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        group: Optional[Group] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.group = group
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["EditGroupInfoResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            group=Group._parse(client, data.get("group")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class BanGroupMemberResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        timestamp: Optional[str] = None,
        group: Optional[Group] = None,
    ):
        super().__init__(client)
        self.timestamp = timestamp
        self.group = group

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["BanGroupMemberResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            timestamp=data.get("timestamp"),
            group=Group._parse(client, data.get("group")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class SetGroupAdminResult(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        in_chat_member: Optional[GroupMember] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.in_chat_member = in_chat_member
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SetGroupAdminResult"]:
        if data is None:
            return None
        result = cls(
            client=client,
            in_chat_member=GroupMember._parse(client, data.get("in_chat_member")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class GroupInfo(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        group: Optional[Group] = None,
        chat: Optional[Chat] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.group = group
        self.chat = chat
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["GroupInfo"]:
        if data is None:
            return None
        result = cls(
            client=client,
            group=Group._parse(client, data.get("group")),
            chat=Chat._parse(client, data.get("chat")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ChannelInfo(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        channel: Optional[Channel] = None,
        chat: Optional[Chat] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.channel = channel
        self.chat = chat
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ChannelInfo"]:
        if data is None:
            return None
        result = cls(
            client=client,
            channel=Channel._parse(client, data.get("channel")),
            chat=Chat._parse(client, data.get("chat")),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class GroupMembers(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        in_chat_members: Optional[list[GroupMember]] = None,
        next_start_id: Optional[str] = None,
        has_continue: Optional[bool] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.in_chat_members = in_chat_members or []
        self.next_start_id = next_start_id
        self.has_continue = has_continue
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["GroupMembers"]:
        if data is None:
            return None
        result = cls(
            client=client,
            in_chat_members=[GroupMember._parse(client, item) for item in data.get("in_chat_members", [])],
            next_start_id=data.get("next_start_id"),
            has_continue=data.get("has_continue"),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class GroupDefaultAccess(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        access_list: Optional[list[str]] = None,
    ):
        super().__init__(client)
        self.access_list = access_list or []

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["GroupDefaultAccess"]:
        if data is None:
            return None
        result = cls(
            client=client,
            access_list=data.get("access_list") or [],
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class PendingObjectOwner(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        exist_pending_owner: Optional[bool] = None,
    ):
        super().__init__(client)
        self.exist_pending_owner = exist_pending_owner

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["PendingObjectOwner"]:
        if data is None:
            return None
        result = cls(
            client=client,
            exist_pending_owner=data.get("exist_pending_owner"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class GroupLink(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        join_link: Optional[str] = None,
    ):
        super().__init__(client)
        self.join_link = join_link

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["GroupLink"]:
        if data is None:
            return None
        result = cls(
            client=client,
            join_link=data.get("join_link"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class JoinLinks(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        join_links: Optional[list[str]] = None,
    ):
        super().__init__(client)
        self.join_links = join_links or []

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["JoinLinks"]:
        if data is None:
            return None
        result = cls(
            client=client,
            join_links=data.get("join_links") or [],
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class JoinLinkObject(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        type: Optional[str] = None,
        object_guid: Optional[str] = None,
    ):
        super().__init__(client)
        self.type = type
        self.object_guid = object_guid

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["JoinLinkObject"]:
        if data is None:
            return None
        result = cls(
            client=client,
            type=data.get("type"),
            object_guid=data.get("object_guid"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class JoinLinkEntry(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        object_guid: Optional[JoinLinkObject] = None,
        join_link: Optional[str] = None,
        creator_guid: Optional[str] = None,
        create_time: Optional[int] = None,
        request_pending_count: Optional[int] = None,
        request_needed: Optional[bool] = None,
        usage_limit: Optional[int] = None,
        title: Optional[str] = None,
        expire_time: Optional[int] = None,
        expire_at: Optional[int] = None,
    ):
        super().__init__(client)
        self.object_guid = object_guid
        self.join_link = join_link
        self.creator_guid = creator_guid
        self.create_time = create_time
        self.request_pending_count = request_pending_count
        self.request_needed = request_needed
        self.usage_limit = usage_limit
        self.title = title
        self.expire_time = expire_time
        self.expire_at = expire_at

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["JoinLinkEntry"]:
        if data is None:
            return None
        result = cls(
            client=client,
            object_guid=JoinLinkObject._parse(client, data.get("object_guid")),
            join_link=data.get("join_link"),
            creator_guid=data.get("creator_guid"),
            create_time=data.get("create_time"),
            request_pending_count=data.get("request_pending_count"),
            request_needed=data.get("request_needed"),
            usage_limit=data.get("usage_limit"),
            title=data.get("title"),
            expire_time=data.get("expire_time"),
            expire_at=data.get("expire_at"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class CreatedJoinLink(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        join_link: Optional[JoinLinkEntry] = None,
    ):
        super().__init__(client)
        self.join_link = join_link

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["CreatedJoinLink"]:
        if data is None:
            return None
        result = cls(
            client=client,
            join_link=JoinLinkEntry._parse(client, data.get("join_link")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class InlineOpenUrlData(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        title: Optional[str] = None,
        url: Optional[str] = None,
    ):
        super().__init__(client)
        self.title = title
        self.url = url

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["InlineOpenUrlData"]:
        if data is None:
            return None
        result = cls(
            client=client,
            title=data.get("title"),
            url=data.get("url"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ProfileLink(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        type: Optional[str] = None,
        inline_open_url_data: Optional[InlineOpenUrlData] = None,
    ):
        super().__init__(client)
        self.type = type
        self.inline_open_url_data = inline_open_url_data

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ProfileLink"]:
        if data is None:
            return None
        result = cls(
            client=client,
            type=data.get("type"),
            inline_open_url_data=InlineOpenUrlData._parse(client, data.get("inline_open_url_data")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ProfileLinkItem(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        title: Optional[str] = None,
        link: Optional[ProfileLink] = None,
    ):
        super().__init__(client)
        self.title = title
        self.link = link

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ProfileLinkItem"]:
        if data is None:
            return None
        result = cls(
            client=client,
            title=data.get("title"),
            link=ProfileLink._parse(client, data.get("link")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ProfileLinkItems(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        link_items: Optional[list[ProfileLinkItem]] = None,
    ):
        super().__init__(client)
        self.link_items = link_items or []

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ProfileLinkItems"]:
        if data is None:
            return None
        result = cls(
            client=client,
            link_items=[ProfileLinkItem._parse(client, item) for item in data.get("link_items", [])],
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class NotificationMessageData(RawObject):
    pass


class ShowNotification(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        notification_id: Optional[str] = None,
        type: Optional[str] = None,
        title: Optional[str] = None,
        text: Optional[str] = None,
        message_data: Optional[NotificationMessageData] = None,
    ):
        super().__init__(client)
        self.notification_id = notification_id
        self.type = type
        self.title = title
        self.text = text
        self.message_data = message_data

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ShowNotification"]:
        if data is None:
            return None
        result = cls(
            client=client,
            notification_id=data.get("notification_id"),
            type=data.get("type"),
            title=data.get("title"),
            text=data.get("text"),
            message_data=NotificationMessageData._parse(client, data.get("message_data")),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class SocketChatUpdate(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        object_guid: Optional[str] = None,
        action: Optional[str] = None,
        chat: Optional[Chat] = None,
        updated_parameters: Optional[list[str]] = None,
        timestamp: Optional[str] = None,
        type: Optional[str] = None,
    ):
        super().__init__(client)
        self.object_guid = object_guid
        self.action = action
        self.chat = chat
        self.updated_parameters = updated_parameters or []
        self.timestamp = timestamp
        self.type = type

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SocketChatUpdate"]:
        if data is None:
            return None
        result = cls(
            client=client,
            object_guid=data.get("object_guid"),
            action=data.get("action"),
            chat=Chat._parse(client, data.get("chat")),
            updated_parameters=data.get("updated_parameters") or [],
            timestamp=data.get("timestamp"),
            type=data.get("type"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class SocketMessageUpdate(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        message_id: Optional[str] = None,
        action: Optional[str] = None,
        message: Optional[Message] = None,
        updated_parameters: Optional[list[str]] = None,
        timestamp: Optional[str] = None,
        prev_message_id: Optional[str] = None,
        object_guid: Optional[str] = None,
        type: Optional[str] = None,
        state: Optional[str] = None,
        is_scheduled: Optional[bool] = None,
    ):
        super().__init__(client)
        self.message_id = message_id
        self.action = action
        self.message = message
        self.updated_parameters = updated_parameters or []
        self.timestamp = timestamp
        self.prev_message_id = prev_message_id
        self.object_guid = object_guid
        self.type = type
        self.state = state
        self.is_scheduled = is_scheduled

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SocketMessageUpdate"]:
        if data is None:
            return None
        result = cls(
            client=client,
            message_id=data.get("message_id"),
            action=data.get("action"),
            message=Message._parse(client, data.get("message")),
            updated_parameters=data.get("updated_parameters") or [],
            timestamp=data.get("timestamp"),
            prev_message_id=data.get("prev_message_id"),
            object_guid=data.get("object_guid"),
            type=data.get("type"),
            state=data.get("state"),
            is_scheduled=data.get("is_scheduled"),
        )
        if result.message is not None:
            setattr(result.message, "action", result.action)
            setattr(result.message, "chat_type", result.type)
            setattr(result.message, "state", result.state)
            setattr(result.message, "is_scheduled", result.is_scheduled)
            setattr(result.message, "prev_message_id", result.prev_message_id)
            if getattr(result.message, "object_guid", None) is None:
                setattr(result.message, "object_guid", result.object_guid)
            if getattr(result.message, "message_id", None) is None:
                setattr(result.message, "message_id", result.message_id)
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class SocketUpdates(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        chat_updates: Optional[list[SocketChatUpdate]] = None,
        message_updates: Optional[list[SocketMessageUpdate]] = None,
        show_notifications: Optional[list[ShowNotification]] = None,
        user_guid: Optional[str] = None,
    ):
        super().__init__(client)
        self.chat_updates = chat_updates or []
        self.message_updates = message_updates or []
        self.show_notifications = show_notifications or []
        self.user_guid = user_guid

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["SocketUpdates"]:
        if data is None:
            return None
        result = cls(
            client=client,
            chat_updates=[SocketChatUpdate._parse(client, item) for item in data.get("chat_updates", [])],
            message_updates=[SocketMessageUpdate._parse(client, item) for item in data.get("message_updates", [])],
            show_notifications=[ShowNotification._parse(client, item) for item in data.get("show_notifications", [])],
            user_guid=data.get("user_guid"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result


class ChatsUpdates(Object):
    def __init__(
        self,
        *,
        client: Any = None,
        chats: Optional[list[RawObject]] = None,
        new_state: Optional[int] = None,
        status: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(client)
        self.chats = chats or []
        self.new_state = new_state
        self.status = status
        self.timestamp = timestamp

    @classmethod
    def _parse(cls, client: Any, data: Optional[dict[str, Any]]) -> Optional["ChatsUpdates"]:
        if data is None:
            return None
        result = cls(
            client=client,
            chats=[RawObject._parse(client, item) for item in data.get("chats", [])],
            new_state=data.get("new_state"),
            status=data.get("status"),
            timestamp=data.get("timestamp"),
        )
        _apply_unknown_fields(result, client, data, result.__dict__.keys())
        return result
