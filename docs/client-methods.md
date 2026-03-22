# Client Methods Reference

This document describes the current public `Client` API and the typed objects returned by each method.

Peer-aware methods:
- methods that previously accepted `object_guid` can still use it unchanged
- the same methods now also accept `peer=` with a `rubigram.Peer`, a typed object, or any object carrying `object_guid` / `user_guid`

Unified client modes:
- `Client(..., phone_number=...)` or interactive auth uses the user session flow
- `Client(..., token="...")` uses the bot API flow with the same session storage and session string format

## Authentication and Session

### `await app.start() -> Client`
Starts the client.

What it does:
- Opens storage
- Refreshes DC configuration
- Loads or creates login key material
- Initializes HTTP transport
- Performs socket handshake if an authenticated session exists
- Runs `registerDevice` when required
- Starts the update listener when possible

### `await app.stop() -> None`
Stops the client and closes:
- websocket transport
- HTTP transport
- DC discovery client
- storage connection

### `await app.export_session_string() -> str`
Exports the current session state as a JSON base64-url-safe session string.

Persisted fields include:
- `api_version`
- `api_url`
- `api_urls`
- `storages`
- `cdn_urls`
- `sockets`
- `auth`
- `tmp_session`
- `public_key`
- `private_key_pem`
- `user_guid`
- `updates_state`
- `device_hash`
- `registered_device`
- `registered_device_version`

## Login Flow

### `await app.send_code(phone_number: str) -> SentCode`
Sends an OTP/login code.

Returned object:
- `SentCode.phone_code_hash`
- `SentCode.status`
- `SentCode.code_digits_count`
- `SentCode.has_confirmed_recovery_email`
- `SentCode.no_recovery_alert`
- `SentCode.send_type`

Typical Rubika data shape:

```python
SentCode(
    phone_code_hash="38044635070003564482129527665122",
    status="OK",
    code_digits_count=6,
    has_confirmed_recovery_email=False,
    no_recovery_alert="...",
    send_type="SMS",
)
```

### `await app.sign_in(phone_number, phone_code_hash, phone_code) -> Authorization`
Signs in with the OTP code.

Returned object:
- `Authorization.status`
- `Authorization.auth`
- `Authorization.user`
- `Authorization.timestamp`

Notes:
- `Authorization.auth` is the encrypted auth returned by Rubika at the payload level.
- Rubigram unwraps and stores the usable session auth internally after success.

### `await app.sign_up(first_name, last_name="") -> Authorization`
Completes registration for a new user when required.

### `await app.register_device(force: bool = False) -> Empty`
Registers the current device/session with Rubika.

Returned object:
- `Empty` (an empty typed object)

## User and Chat Methods

### `await app.get_user_info(user_guid: str) -> UserInfo`
Returns detailed information about a user and its chat relation.

Returned object:
- `UserInfo.user`
- `UserInfo.chat`
- `UserInfo.timestamp`
- `UserInfo.is_in_contact`
- `UserInfo.can_receive_call`
- `UserInfo.can_video_call`
- `UserInfo.user_additional_info`

Common nested objects:
- `User`
- `Chat`
- `OnlineTime`
- `UserAdditionalInfo`

### `await app.get_me() -> UserInfo`
Equivalent to `get_user_info()` using the authenticated `user_guid` stored in session.

### `await app.get_object_by_username(username: str) -> ObjectByUsername`
Looks up a user/chat by username.

Returned object:
- `ObjectByUsername.exist`
- `ObjectByUsername.type`
- `ObjectByUsername.user`
- `ObjectByUsername.chat`
- `ObjectByUsername.timestamp`
- `ObjectByUsername.is_in_contact`

### `await app.get_avatars(object_guid: str) -> ChatAvatars`
Returns avatars for a user or chat.

Returned object:
- `ChatAvatars.avatars`

Nested:
- `Avatar.avatar_id`
- `Avatar.thumbnail`
- `Avatar.main`
- `Avatar.create_time`

### `await app.get_contacts(offset=0, limit=100) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`
- can be typed further later

### `await app.get_chat(object_guid: str) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.get_messages(object_guid: str, offset=0, limit=20) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.get_history(object_guid: str, offset=0, limit=50) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.get_chats_updates(state: int | None = None) -> ChatsUpdates`
Polls `getChatsUpdates`.

Returned object:
- `ChatsUpdates.chats`
- `ChatsUpdates.new_state`
- `ChatsUpdates.status`
- `ChatsUpdates.timestamp`

If `state` is omitted:
- Rubigram uses `storage.updates_state()`
- if no stored state exists, it starts from current Unix time

## Messaging

### `await app.request_send_file(file_name: str, size: int, mime: str) -> UploadDescriptor`
Requests an upload slot from Rubika before sending media bytes.

Returned object:
- `UploadDescriptor.id`
- `UploadDescriptor.dc_id`
- `UploadDescriptor.access_hash_send`
- `UploadDescriptor.upload_url`
- `UploadDescriptor.access_hash_rec`

Typical Rubika data shape:

```python
UploadDescriptor(
    id="87998036915657",
    dc_id="491",
    access_hash_send="euthauxjfybzjbaaymlitbhpio8651",
    upload_url="https://upmessenger491.iranlms.ir/UploadFile.ashx",
)
```

### `await app.send_message(object_guid, rnd, text, parse_mode=None, reply_to_message_id=None) -> SentMessage`
Sends a text message.

Returned object:
- `SentMessage.message_update`
- `SentMessage.status`
- `SentMessage.chat_update`

Common nested payload:
- `message_update.message_id`
- `message_update.message.text`
- `chat_update.chat.last_message`

### `await app.send_voice(object_guid, path, rnd=None, duration_ms=0, mime=None) -> SentMessage`
Uploads a local voice file and sends it as a `Voice` media message.

Current implemented flow:
1. `requestSendFile`
2. binary upload to `UploadFile.ashx`
3. `sendMessage` with `file_inline`

Current file-inline payload shape:

```python
{
    "file_name": "voice.ogg",
    "time": 720,
    "size": 1654,
    "type": "Voice",
    "dc_id": "491",
    "file_id": "87998036915657",
    "mime": "ogg",
    "access_hash_rec": "1827275907694936106542107050922026031521",
}
```

Notes:
- `duration_ms` is currently explicit. Rubigram does not yet derive OGG/Opus duration automatically.
- This upload pipeline is designed to be reused later for `send_photo`, `send_video`, and `send_document`.

### `await app.download_file(file, path=None, *, in_memory=False, file_name=None) -> bytes | Path`
Downloads media using Rubika `GetFile.ashx` chunked requests.

Accepted input objects:
- `Message` with `file_inline`
- `Message` with `sticker.file`
- `FileInline`
- `StickerFile`
- `Sticker`

Behavior:
- if `in_memory=True`, returns `bytes`
- otherwise returns the downloaded `Path`
- if `path` is a directory, Rubigram uses the media file name
- `progress(current, total, *progress_args)` is called during download

Related bound methods:
- `await message.download(...)`
- `await message.file_inline.download(...)`
- `await message.sticker.download(...)`

### `await app.send_music(object_guid, path, *, duration_ms, rnd=None, mime=None, progress=None, progress_args=()) -> SentMessage`
Uploads a local audio file and sends it as a `Music` media message.

### `await app.send_photo(object_guid, path, *, rnd=None, mime=None, text=None, width=None, height=None, progress=None, progress_args=()) -> SentMessage`
Uploads a local image and sends it as an `Image` media message.

### `await app.send_document(object_guid, path, *, rnd=None, mime=None, text=None, progress=None, progress_args=()) -> SentMessage`
Uploads a local file and sends it as a generic `File` media message.

Notes:
- current implementation expects `duration_ms` explicitly
- `progress(current, total, *progress_args)` is called during upload

### `await app.send_video(object_guid, path, *, duration_ms, width, height, rnd=None, mime=None, text=None, is_round=False, is_spoil=False, progress=None, progress_args=()) -> SentMessage`
Uploads a local video file and sends it as a `Video` media message.

Notes:
- current implementation expects `duration_ms`, `width`, and `height` explicitly
- if `text` is provided, it is sent as caption
- `progress(current, total, *progress_args)` is called during upload

### `await app.edit_message(object_guid, message_id, text) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.delete_message(object_guid, message_id) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.block_user(object_guid) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

### `await app.unblock_user(object_guid) -> RawObject`
Current status:
- implemented
- still returned as `RawObject`

## Websocket Updates

### `await app.receive_socket_update(timeout: float | None = None) -> SocketUpdates`
Waits for the next websocket messenger update and returns a typed update object.

Returned object:
- `SocketUpdates.chat_updates`
- `SocketUpdates.message_updates`
- `SocketUpdates.show_notifications`
- `SocketUpdates.user_guid`

Nested objects:
- `SocketChatUpdate`
- `SocketMessageUpdate`
- `ShowNotification`
- `NotificationMessageData`

Message-specific nested structures currently parsed:
- `message.forwarded_from`
- `message.file_inline`
- `message.sticker`
- `message.rubino_post_data`
- `message.live_data`

## Callbacks

### `@app.on_message(filter=None)`
Registers a message handler for websocket `message_updates`.

Example:

```python
from rubigram import Client, filters

app = Client("my_account")


@app.on_message(filters.text & filters.private & ~filters.me)
async def handler(client, message):
    print(message.text)
    await message.reply("received")
```

### `await app.idle() -> None`
Keeps the process alive while the update listener is running.

## Message Convenience Methods

`Message` objects currently include:

### `await message.reply(text: str, parse_mode: str | None = None) -> Any`
Uses:
- `message.object_guid`
- `message.message_id`

Internally calls:
- `client.send_message(..., reply_to_message_id=message.message_id)`

### `message.chat_id`
Alias for:
- `message.object_guid`

## Filter System

Available from:

```python
from rubigram import filters
```

Current filters include:
- `filters.all`
- `filters.me`
- `filters.private`
- `filters.bot`
- `filters.group`
- `filters.channel`
- `filters.service`
- `filters.text`
- `filters.media`
- `filters.photo`
- `filters.video`
- `filters.voice`
- `filters.music`
- `filters.gif`
- `filters.document`
- `filters.sticker`
- `filters.rubino`
- `filters.live`
- `filters.caption`
- `filters.poll`
- `filters.quiz`
- `filters.event`
- `filters.new`
- `filters.edited`
- `filters.deleted`
- `filters.replied`
- `filters.forwarded`
- `filters.forwarded_no_link`
- `filters.bold`
- `filters.mono`
- `filters.italic`
- `filters.mention`
- `filters.member_added`
- `filters.member_joined`
- `filters.member_left`
- `filters.member_removed`
- `filters.message_pinned`
- `filters.voice_chat_started`
- `filters.voice_chat_finished`
- `filters.regex(pattern)`
- `filters.group_link`
- `filters.channel_link`

Composition is supported:

```python
filters.text & filters.private
filters.photo | filters.video
~filters.me
```

## Notes

Methods that still return `RawObject` are implemented and usable, but their result schema has not yet been locked into a dedicated typed model.

That is the current boundary between:
- stable typed API
- raw-but-usable API

