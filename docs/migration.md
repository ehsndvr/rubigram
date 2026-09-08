# Migrating from rubigram 0.1

Most 0.1 code keeps working; renamed names are kept as aliases that emit a
`DeprecationWarning`. This page lists what changed and what to replace.

## Imports

| 0.1 | 0.2 |
|---|---|
| `from rubigram.exceptions import InvalidInput` | `from rubigram.errors import InvalidInput` (old module warns) |
| `from rubigram.types.results import Message` | `from rubigram.types import Message` (old module warns) |
| `from rubigram.bot.types import Keypad` / `rubigram.bot.enums` | `rubigram.types.bot` / `rubigram.enums` (old modules warn) |
| `from rubigram.bot.client import BotClient` | removed: `Client("name", token=…)` |
| `rubigram.network.transport.RpcTransport` | `rubigram.network.HttpTransport` (alias kept) |
| `rubigram.network.socket.SocketTransport` | `rubigram.network.SocketTransport` |
| `rubigram.storage.FileStorage` | `rubigram.storage.SqliteStorage` (alias kept) |
| `rubigram.session`, `rubigram.methods`, `rubigram.crypto.encryption` | removed; use `Client`, `rubigram.crypto.cipher` / `codec` |

## Client

| 0.1 | 0.2 |
|---|---|
| `Client(name, interactive_auth=…, enable_socket_handshake=…, socket_heartbeat_interval=…)` | still accepted; new names `interactive=`, `enable_socket=`, `socket_heartbeat_interval=` |
| `await app.authorize()` | `await app.login(phone_number=…, code=… / code_callback=…)` (`authorize` still works) |
| prompts on the console | only when `interactive=True` (default) **and** stdin is a terminal; otherwise `LoginRequired` |
| `receive_socket_update()` | `receive_update()` (alias kept) |
| `start_polling()` / `stop_polling()` | `run()` / `idle()` / `stop()` (old names kept) |
| `app.timeout`, `app.proxy` | same, plus `retry_policy=`, `user_agent=`, `transport=` |

`start()` no longer starts a background update loop unless handlers are
registered (or `idle()` is called), so scripts that only call methods do not
poll in the background.

## Methods

| 0.1 | 0.2 | Reason |
|---|---|---|
| `send_message(guid, rnd, text)` | `send_message(guid, text)`; `rnd=` is a keyword and generated for you | positional order was error-prone; a warning fixes the old order |
| `get_history(guid, offset, limit)` | `get_messages(guid, max_id=, min_id=, sort=, limit=, filter_type=)` | the web client calls `getMessages`; `getHistory` does not exist |
| `get_chat(guid)` → `RawObject` | `get_chat(guid)` → `Chat` (via `getChatsByID`) | `getChat` does not exist server-side |
| `delete_message(guid, id)` | `delete_messages(guid, [ids], delete_type=)` (`delete_message` still works) | `deleteMessage` does not exist server-side |
| `block_user` / `unblock_user` | same names, now `setBlockUser` with `Block`/`Unblock` | `blockUser`/`unblockUser` do not exist |
| `upload_group_avatar(guid, path)` | `set_group_photo(guid, path)` / `upload_avatar(guid, path)` | `uploadNewGroupAvatar` does not exist; `uploadAvatar` is the real call |
| `send_uploaded_media(object_guid=, path=, media_type=)` | `send_media(guid, path, media_type=…)` and `send_photo/video/voice/music/gif/document` | |
| `get_contacts(offset, limit)` | `get_contacts(start_id=)` | the real input is `start_id` |
| `get_messages(guid, offset, limit)` | `get_messages(guid, max_id=…)` | |
| `get_rubino_post(...)` → `RawObject` | `RubinoPostsResult` with `.post`, downloadable files | |
| `download_file(...)` host `messenger{dc}.iranlms.ir` | the `storages[dc_id]` host from `getDCs` | old host pattern was wrong |

Every method that returned `RawObject` for a known payload now returns a typed
model; unknown keys stay reachable through `.extra` and as attributes, so
`result.some_field` keeps working.

## Filters and handlers

Filters are the same objects and still compose with `&`, `|`, `~`, but their
`__call__` is `async` (handlers await them). Custom filters written as
`filters.create(lambda client, message: …)` keep working; `filter.check_sync()`
exists for synchronous evaluation. New decorators: `on_edited_message`,
`on_deleted_message`, `on_chat_update`, `on_activity`, `on_notification`,
`on_draft_update`, `on_callback_query`, `on_raw_update`; handlers can raise
`StopPropagation` / `ContinuePropagation` and are grouped with `group=`.

## Errors

`RpcError` keeps `status`, `status_det` and `raw`; `raw` is now the decrypted
payload that carried the error (0.1 stored the outer envelope for inner
errors). Old aliases (`RubikaError`, `AuthKeyInvalid`, `RegisterDeviceRequired`,
`FloodWaitError`, `PhoneCodeInvalid`, `PhoneHashInvalid`) still resolve to the
new classes.

## Session files

0.1 SQLite sessions open unchanged; the schema is upgraded in place (new
columns, `meta.version = 2`). The 0.1 session string format is accepted by
`import_session_string()` / `from_session_string()`; exports use the new
`rbg2.` format.
