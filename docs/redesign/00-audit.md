# Phase 0 audit — rubigram before the redesign

Date: 2026-09-07. Branch: `claude/rubigram-balegram-redesign-80eb77` (worktree of
`C:\Codes\rubigram`, based on `master` at `501cfc8`). Reference project:
`E:\Codes\balegram` (read-only).

This document records what existed before any architectural change, so that the
redesign can be checked against it. Nothing in this file contains keys, phone
numbers, auth strings or GUIDs from the owner's sessions.

## 1. Rescued uncommitted work

The owner's unsaved work lived only in the main checkout (`C:\Codes\rubigram`);
the worktree started clean. All 14 modified files and the 3 non-junk untracked
files were copied verbatim and committed as `c0ed041`
("نجات کار ذخیره‌نشدهٔ مالک … — Rescue owner's uncommitted work …").

| File | Change | Apparent purpose |
|---|---|---|
| `README.md` | +1 line | Lists `get_rubino_post` in the public surface |
| `docs/client-methods.md` | +38 | Documents `get_rubino_post` and `get_base_info` |
| `rubigram/client.py` | +434 (CRLF noise inflates it) | `get_rubino_post`, `get_base_info`, `download_url`, Rubino transport lifecycle, `_build_dc_urls` family, `_ensure_base_info`, `_service_client_info` (platform `PWA`), `_resolve_rubino_post_input` |
| `rubigram/enums/__init__.py` | +2 | Exports `DcType` |
| `rubigram/enums/dc_type.py` | new | `DcType` enum: api/bot/dcs/rubino/socket/wallet |
| `rubigram/network/discovery.py` | +121 | `BASE_INFO_URL` (servicesbase), `fetch_base_info` (`getBaseInfo`, api_version "0"), `urls_for`, `suggested_urls_for`, URL collectors |
| `rubigram/network/download.py` | +70 | `download_url` (streamed GET with progress) |
| `rubigram/network/transport.py` | +110 | `JsonTransport` (plain JSON POST with pool failover); `_refresh_pool` uses `urls_for` |
| `rubigram/storage/file_storage.py` | +3 | `suggested_urls_json` column + ALTER TABLE migration |
| `rubigram/storage/sqlite_storage.py` | +19 | `suggested_urls` getter/setter, in export/import dict |
| `rubigram/types/__init__.py` | +8 | Exports `RubinoPost`, `RubinoPostMedia`, `RubinoPostsResult`, `UrlFile` |
| `rubigram/types/results.py` | +326 | `UrlFile`, `RubinoPostMedia`, `RubinoPost`, `RubinoPostsResult`, `_download_bound_url`, `_rubino_default_name` |
| `tests/local_client_test.py` | reformat + new handler | Real-account script now fetches and downloads a Rubino post |
| `tests/test_client.py` | +342 | 5 new tests for base info / Rubino post / download helpers |
| `tests/test_transport.py` | +198 | Tests for `urls_for`, `suggested_urls_for`, `JsonTransport`, `download_url` |
| `examples/get_rubino_post.py` | new | Example script for the Rubino flow |
| `tests/rubino_downloader_bot.py` | new | Real-account script: re-sends Rubino post media to the chat (belongs in `examples/`, not `tests/`) |

Verdict: the work is coherent and compiles. One of its own new tests fails
(see section 2); the cause is a `MemoryStorage` limitation, not a logic error in
the feature.

## 2. Test baseline (`python -m pytest -q`)

| State | Result |
|---|---|
| Committed HEAD `501cfc8` | 10 failed, 118 passed |
| After rescue `c0ed041` | 11 failed, 126 passed |

Diagnosis of every failure (these are the starting point; the redesign must
either fix the library bug or correct the stale test):

| Test | Root cause | Kind |
|---|---|---|
| `test_client_start_refreshes_base_info_when_auth_exists` (new) | `MemoryStorage.open()` creates a fresh `:memory:` database, so the auth set before `start()` is wiped and `_ensure_base_info` never runs | library limitation (in-memory storage not reopen-safe) |
| `test_phone_number_with_common_separators_is_not_detected_as_bot_token` | test input has 10 digits after the `0` while the expectation assumes 9; `_normalize_phone_number` turns `09…` into `989…` | test expectation inconsistent; normalizer rules undocumented |
| `test_chat_avatars_is_list_like_and_avatar_downloads_main_file`, `test_chat_avatars_download_downloads_all_with_generated_names` | the `download`/`_select_download_file`/`_default_download_name` methods were pasted into `SearchGlobalObjectsResult` instead of `Avatar` (`results.py` ~1198–1230) | library bug |
| `test_edit_channel_info_accepts_peer_objects` | `EditChannelInfo` never imported in the test | test bug |
| `test_request_change_object_owner_raises_invalid_auth_with_raw_payload`, `test_remove_group_raises_invalid_auth_with_raw_payload` | `_invoke_once` passes the outer encrypted envelope as `raw`; the decrypted payload with `client_show_message` is not exposed on the error | library bug (errors hide the server's human-readable message) |
| `test_message_reply_uses_send_message_with_reply_to` | test stub lacks the `entities` kwarg that `Message.reply` now passes | test bug |
| `test_message_parses_rubino_sticker_voice_gif_and_live_payloads` | `Sticker._parse` parses via `RawObject` (which already converts `file` to a `RawObject`) and then calls `StickerFile._parse` on it, which does `data.get` | library bug: any sticker in a socket frame raises inside `SocketUpdates._parse`, and `_update_listener_loop` only recovers from transport errors, so one sticker message kills the update listener |
| `test_rpc_headers_match_browser_profile` | test expects `sec-ch-ua-platform`; `build_rpc_headers` has no `sec-ch-ua*` headers | to be settled by Phase 1 (real browser headers) |
| `test_socket_transport_disables_proxy_and_sends_browserish_headers` | commit `501cfc8` removed `proxy`/`additional_headers` from `websockets.connect` but the test was not updated | test stale; Phase 1 decides the real WS headers, redesign adds proxy support properly |

The three `tests/local_*.py` files and `tests/rubino_downloader_bot.py` are not
collected by pytest (`python_files = test_*.py`); they are scripts against real
accounts (see section 7).

## 3. Package inventory and problems

10,569 lines of Python at HEAD, about 11,200 after the rescue. Biggest files:
`types/results.py` (2,323), `client.py` (1,536), `bot/types.py` (1,032),
`bot/client.py` (429), `methods/chats/groups.py` (410), `raw/methods/groups.py` (391).

| Module | Lines | Problems found by reading |
|---|---|---|
| `client.py` | 1,536 | God class: lifecycle, DC discovery, login prompts (`print`/`input`), invoke + decrypt, socket update loop, handler dispatch (own `MessageHandler`), bot polling loop, bot payload helpers, markdown/HTML entity parser, OGG/Opus duration parser, download destination logic, Rubino URL resolution. Duplicates mixin helpers (`_guess_upload_mime`, `_send_uploaded_media`, `_upload_file`). `print()` in `start()` failure path and the whole authorize flow. `__enter__` calls `asyncio.run` (unusable inside a running loop). |
| `types/results.py` | 2,323 | Single file for ~70 classes; hand-written `__init__`+`_parse` pairs; `Avatar.download` misplaced; `Sticker._parse` double-parse bug; `MessageUpdate`/`ChatUpdate` are bare `RawObject`s while `SocketMessageUpdate`/`SocketChatUpdate` are typed (two models for the same server object). |
| `bot/` (client, types, enums, transport) | 1,643 | Second Bot API implementation (`BotClient`) parallel to `methods/bots/api.py` + `Client` bot branches. `bot/types.py` mixes `@dataclass` decorators with hand-written `__init__` (the dataclass fields are dead). Not exported anywhere except `rubigram.bot`. |
| `methods/bots/api.py`, `methods/chats/bot_updates.py` | 333 | Bot API inside `Client`; every method starts with `if not self.is_bot: raise RuntimeError`. Polling loop lives in `client.py`. |
| `methods/*` | ~1,570 | Good mixin direction, but: `Medias.upload_file` shadowed by `Bots.upload_file` in the MRO; `send_uploaded_media` public duplicate of `Client._send_uploaded_media`; `users/block_user.py` is empty; `get_chat`, `get_messages`, `get_history`, `get_contacts`, `add_group_members`, `set_group_default_access`, `remove_group`, `request_change_object_owner`, `block_user`, `unblock_user`, `edit_message`, `delete_message`, `upload_group_avatar` still return `RawObject`. |
| `raw/methods/*` | 1,190 | One dataclass per RPC with `to_input` + `parse_response`; serialization is fine but `parse_response` duplicates the same 3 lines per class; no builders/methods split. `GetChannelLink` returns `Empty` although the server returns a join link. |
| `raw/base.py` | 43 | OK. `auth_mode` literal `"auth"/"tmp"` drives the envelope. |
| `network/transport.py` | 283 | `RpcTransport` (encrypted envelope, failover, pool refresh) and `JsonTransport` copy the same retry loop. No retry/backoff for transient errors, no proxy, no per-call timeout. |
| `network/socket.py` | 224 | Handshake, `{}` heartbeat every 30 s, reader queue. No automatic reconnect (callers re-handshake), no proxy, no request/response correlation (the socket is receive-only today). |
| `network/discovery.py` | 187 | `getDCs` (api_version 4) and `getBaseInfo` (api_version 0). Hard-coded client info duplicated from `Client`. |
| `network/upload.py`, `download.py` | 119 / 203 | Chunked upload/download with progress; reads whole file into memory for upload; no retry. |
| `network/headers.py` | 92 | Browser header profiles; lacks `sec-ch-ua*`; to be validated in Phase 1. |
| `crypto/*` | 360 | Correct and tested (AES-CBC, caesar, RSA sign/unwrap, key export). `encryption.py` is a legacy re-export shim. |
| `storage/*` | 424 | `SQLiteStorage` ABC + `FileStorage` + `MemoryStorage`; session string = base64url(JSON) of every field, unversioned and unencrypted; `MemoryStorage.open()` discards state; migrations by ad-hoc `ALTER TABLE` in `FileStorage` only. |
| `storage/session_string.py` | 26 | Unversioned, no integrity check, embeds the private key PEM. |
| `exceptions/` + `errors/` | 204 + 57 | Two packages for one hierarchy; `map_rpc_error` matches on substrings of the lowercase message, so `INVALID_AUTH` maps to `AuthKeyInvalid` only because "auth" and "invalid" appear; no `retry_after`; `client_show_message` dropped. |
| `filters.py` | 140 | Sync-only `Filter` dataclass with `&`, `|`, `~`; message-only. Fine as a base. |
| `peer.py` | 32 | `Peer.from_value` accepts str / typed objects. Keep. |
| `types/object.py` | 106 | Pyrogram-style `Object` base with JSON `__str__`, bind, pickling. Keep. |
| `types/user_and_chats/*` | 181 | Pyrogram copy-paste: `chat_avatar.py` uses `Object` without importing it (NameError on import), `user.py` references `raw.types.UserEmpty` which does not exist. Never imported. Dead. |
| `types/formatting.py`, `enums/*` | 37 / 89 | Fine. |
| `session/__init__.py` | 10 | Re-export shim of `storage`. Never imported. Dead. |
| `utils/__init__.py` | 44 | `generate_tmp_session` uses `random` (not `secrets`). |
| `models/`, `api/` | 0 | Empty directories in the main checkout only (untracked, not in the worktree). |

## 4. Module dependency map (typed method → raw method → transport → result)

Transports: **RPC** = `RpcTransport` HTTPS POST of the encrypted envelope to a
`messengerg2c*.iranlms.ir` URL from `getDCs`; **tmp** = same envelope keyed by
`tmp_session` (login only); **WS** = `SocketTransport` (`handShake` + pushed
`messenger` frames, receive-only); **UP/DL** = `UploadTransport` /
`DownloadTransport`; **JSON** = `JsonTransport` (plain JSON, Rubino DC);
**BOT** = `BotTransport` (`https://botapi.rubika.ir/v3/{token}/{method}`).

| Public method (mixin) | Raw method | Transport | Returns |
|---|---|---|---|
| `send_code` (auth) | `SendCode` | tmp | `SentCode` |
| `sign_in` | `SignIn` (unwraps `auth`) | tmp | `Authorization` |
| `sign_up` | `SignUp` (unwraps `auth`) | tmp | `Authorization` |
| `register_device` | `RegisterDevice` | RPC | `Empty` |
| `get_user_info` (users) | `GetUserInfo` | RPC | `UserInfo` |
| `get_me` | `GetUserInfo` / bot `getMe` | RPC / BOT | `UserInfo` / `bot.Bot` |
| `get_object_by_username` | `GetObjectByUsername` | RPC | `ObjectByUsername` |
| `get_avatars` | `GetAvatars` | RPC | `ChatAvatars` |
| `get_contacts` | `GetContacts` | RPC | `RawObject` |
| `get_contacts_last_online` | `GetContactsLastOnline` | RPC | `ContactsLastOnline` |
| `get_contacts_updates` | `GetContactsUpdates` | RPC | `ContactsUpdates` |
| `get_profile_link_items` | `GetProfileLinkItems` | RPC | `ProfileLinkItems` |
| `search_global_objects` | `SearchGlobalObjects` | RPC | `SearchGlobalObjectsResult` |
| `block_user` / `unblock_user` | `BlockUser` / `UnblockUser` | RPC | `RawObject` |
| `get_chat` (dialogs) | `GetChat` / bot `getChat` | RPC / BOT | `RawObject` / `bot.Chat` |
| `get_messages`, `get_history` | `GetMessages`, `GetHistory` | RPC | `RawObject` |
| `get_chats_updates` | `GetChatsUpdates` (persists `new_state`) | RPC | `ChatsUpdates` |
| `add_channel`/`create_channel` (channels) | `AddChannel` | RPC | `AddChannelResult` |
| `add_channel_members` | `AddChannelMembers` | RPC | `AddChannelMembersResult` |
| `get_channel_link` | `GetChannelLink` | RPC | `Empty` (wrong) |
| `get_channel_info` | `GetChannelInfo` | RPC | `ChannelInfo` |
| `get_channel_all_members` / `_admin_members` / `get_banned_channel_members` | `GetChannel*Members` | RPC | `GroupMembers` |
| `set_channel_admin` / `update_channel_admin_access` / `unset_channel_admin` | `SetChannelAdmin` | RPC | `SetGroupAdminResult` |
| `edit_channel_info` | `EditChannelInfo` | RPC | `EditChannelInfoResult` |
| `add_group`/`create_group` (groups) | `AddGroup` | RPC | `AddGroupResult` |
| `add_group_members` | `AddGroupMembers` | RPC | `RawObject` |
| `get_group_info` | `GetGroupInfo` | RPC | `GroupInfo` |
| `get_group_all_members` | `GetGroupAllMembers` | RPC | `GroupMembers` |
| `get_group_default_access` / `set_group_default_access` | `GetGroupDefaultAccess` / `SetGroupDefaultAccess` | RPC | `GroupDefaultAccess` / `RawObject` |
| `get_pending_object_owner` | `GetPendingObjectOwner` | RPC | `PendingObjectOwner` |
| `get_group_link` / `get_join_links` / `create_join_link` | `GetGroupLink` / `GetJoinLinks` / `CreateJoinLink` | RPC | `GroupLink` / `JoinLinks` / `CreatedJoinLink` |
| `edit_group_info` + `set_group_event_messages`, `set_group_history_for_new_members`, `set_group_slow_mode`, `set_group_reaction_setting`, `set_group_reactions_all/disabled/selected` | `EditGroupInfo` | RPC | `EditGroupInfoResult` |
| `ban_group_member` / `unban_group_member` | `BanGroupMember` | RPC | `BanGroupMemberResult` |
| `set_group_admin` / `update_group_admin_access` / `unset_group_admin` | `SetGroupAdmin` | RPC | `SetGroupAdminResult` |
| `request_change_object_owner`, `remove_group` | `RequestChangeObjectOwner`, `RemoveGroup` | RPC | `RawObject` |
| `upload_group_avatar` / `set_group_photo` | `RequestSendFile` → UP → `UploadNewGroupAvatar` | RPC+UP | `RawObject` |
| `send_message` (messages) | `SendMessage` / bot `sendMessage` | RPC / BOT | `SentMessage` / `bot.SentMessage` |
| `edit_message`, `delete_message` | `EditMessage`, `DeleteMessage` / bot | RPC / BOT | `RawObject` / bot |
| `delete_chat_history` | `DeleteChatHistory` | RPC | `DeleteChatHistoryResult` |
| `send_chat_activity` / `send_typing` | `SendChatActivity` | RPC | `Empty` |
| `send_photo` / `send_document` / `send_voice` / `send_music` / `send_video` (medias) | `RequestSendFile` → UP → `SendMessage(file_inline)` | RPC+UP | `SentMessage` |
| `request_send_file`, `upload_file`, `download_file`, `download_url` | `RequestSendFile` / UP / DL | RPC, UP, DL | `UploadDescriptor` / `bytes` or `Path` |
| `get_available_reactions` (utils) | `GetAvailableReactions` | RPC | `AvailableReactions` |
| `get_rubino_post` (client) | `getProfilePosts` | JSON | `RubinoPostsResult` |
| `get_base_info` (client) | `getBaseInfo` | discovery HTTPS | `RawObject` |
| `receive_socket_update` (client) | — | WS | `SocketUpdates` |
| `get_updates`, `start_polling`, `stop_polling`, `parse_webhook_update`, `dispatch_webhook_update` (bot_updates) | bot `getUpdates` | BOT | `bot.BotUpdates` / `bot.WebhookUpdate` |
| `send_poll`, `send_location`, `send_contact`, `forward_message`, `edit_message_keypad`, `edit_inline_keypad`, `set_commands`, `update_bot_endpoints`, `edit_chat_keypad`, `get_file`, `upload_bot_file`, `send_file`, `send_media`, `ban_chat_member`, `unban_chat_member` (bots) | bot methods of the same name | BOT | `bot.*` |

Protocol constants used today (to be re-verified live in Phase 1):
RPC `api_version` "6"; socket handshake `api_version` "5"; `getDCs` `api_version`
"4"; `getBaseInfo` `api_version` "0"; client info `Main / 4.4.27 / Web /
web.rubika.ir / fa` (services calls use platform `PWA`); `registerDevice` with
`token_type "Web"`, `app_version "WB_4.4.27"`, `system_version "Windows 10"`,
`device_model "Chrome 145"`, 26-digit numeric `device_hash`; request body is
`text/plain` JSON `{api_version, auth: caesar(auth), data_enc, sign}`
(`sign` = RSA PKCS#1 v1.5/SHA-256 over `data_enc`), login body
`{api_version, tmp_session, data_enc}`; AES-256-CBC with zero IV and key
`create_secret_passphrase(auth)`; server `auth` unwrapped with RSA OAEP-SHA1;
socket heartbeat is the literal `{}` every 30 s; downloads POST
`https://messenger{dc_id}.iranlms.ir/GetFile.ashx` with `Auth`, `Start-Index`,
`Last-Index`, `File-Id`, `Access-Hash-Rec`; uploads POST chunks to
`upload_url` with `Auth`, `File-Id`, `Access-Hash-Send`, `Part-Number`,
`Total-Part`, `Chunk-Size`.

## 5. Duplicates

1. **Bot API twice**: `rubigram/bot/client.py::BotClient` and the `Client` bot
   branches (`methods/bots/api.py`, `methods/chats/bot_updates.py`,
   `client.py::_invoke_bot/_send_bot_message/_bot_polling_loop`). Same
   endpoints, same types, two dispatchers.
2. **Errors twice**: `rubigram/exceptions/__init__.py` defines,
   `rubigram/errors/__init__.py` re-exports.
3. **Upload/send helpers twice**: `Client._send_uploaded_media` vs
   `Medias.send_uploaded_media`; `Client._upload_file` vs `Medias.upload_file`
   (shadowed by `Bots.upload_file`); `Client._guess_upload_mime` vs
   `Utils.guess_upload_mime`.
4. **Retry loop twice**: `RpcTransport.send_payload` and `JsonTransport.send_json`.
5. **Client info twice**: `Client.device_info` and the literal dict inside
   `DcDiscovery.fetch_dcs`.
6. **Schema twice**: `SCHEMA_V1` in `sqlite_storage.py` and the inline
   `CREATE TABLE` in `file_storage.py` (they already drifted: the latter lacks
   `bot_token`/`bot_offset_id` and relies on ALTERs).
7. **Update models twice**: `MessageUpdate`/`ChatUpdate` (raw) vs
   `SocketMessageUpdate`/`SocketChatUpdate` (typed); `bot.types.Message` vs
   `types.Message` (different APIs for "a message").
8. **Storage re-export twice**: `rubigram/storage/__init__.py` and
   `rubigram/session/__init__.py`.
9. **Crypto re-export twice**: `crypto/__init__.py` and `crypto/encryption.py`.
10. **Handler registries twice**: `Client._message_handlers` (with filter) and
    `BotClient._message_handlers` (without).

## 6. Deletion candidates

Status legend: *unused* = no import/reference found (grep over `rubigram/`,
`tests/`, `docs/`, `examples/`, `README.md`); *in use* = referenced; *not
inspected* = still to open. All files below were opened.

| Path (relative to `C:\Codes\rubigram`) | Size | Status | Plan |
|---|---|---|---|
| `._*` AppleDouble files (272 files, in every folder incl. `__pycache__`) | 1.1 MB total, 4 KB each | unused (macOS resource forks) | delete in Phase 3 cleanup; add `._*` to `.gitignore` |
| `.DS_Store` (root, **tracked in git**) | 6 KB | unused | `git rm`; add to `.gitignore` (already listed but tracked before) |
| `local_bot.session`, `my_account.session`, `my_bot.session`, `new_me_bot.session`, `rubino_downloader_bot.session`, `test_client.session` | 16–115 KB | in use only by the real-account scripts (section 7) | delete at the end of Phase 3 after the scripts are moved/marked; never commit |
| `examples.json` (**tracked** although gitignored) | 79 KB | unused by code; holds 41 recorded request/response pairs with real GUIDs, 2 phone numbers, names and access hashes | mine it for sanitized test fixtures in Phase 3/4, then `git rm` |
| `rubigram-ui/` (`index.html`, `app.js`, `styles.css`) | 15 KB | unused; a standalone browser page that decrypts a captured `data_enc` with a given auth (re-implements `crypto.cipher` in JS) | it is a developer tool for traffic inspection, not part of the library: move to `tools/payload-decoder/` with a README line, or delete (decide in Phase 3; recommendation: keep under `tools/`) |
| `rubigram.egg-info/` | 8 KB | build artifact of `pip install -e` | delete; already gitignored |
| `.pytest_tmp/`, `.pytest_cache/` | empty / cache | unused | delete |
| `.vscode/settings.json` | 150 B | editor settings (extraPaths, basic type checking) | keep out of git (already ignored); leave on disk |
| `TODO` (356 B, tracked) | | two done items + one idea (a Rubika AI assistant built on rubigram) | delete; idea preserved in section 9 |
| `TODO.md`, `LICENSE` | 0 B each, tracked | empty | `TODO.md`: delete. `LICENSE`: must become a real license before PyPI (owner decision: MIT recommended) |
| `rubigram/models/`, `rubigram/api/` | empty dirs (main checkout only) | unused | delete |
| `rubigram/session/` | 10 lines | unused shim | delete (add a `DeprecationWarning` shim only if `rubigram.session` is considered public; it was never documented) |
| `rubigram/types/user_and_chats/` | 181 lines | unused, does not even import | delete |
| `rubigram/crypto/encryption.py` | 41 lines | unused shim | delete |
| `rubigram/methods/users/block_user.py` | 0 lines | unused | delete |
| `rubigram/bot/` | 1,643 lines | in use (`Client` imports its types/enums/transport; `tests/test_bot_api.py`, `docs/bot-api.md`) | merge into `types/bot/*`, `network/bot_api.py`, then delete |
| `rubigram/errors/` **or** `rubigram/exceptions/` | | both in use | keep one package (`errors/`), turn the other into a deprecation shim |
| `tests/local_bot_test.py`, `tests/local_client_test.py`, `tests/local_test.py`, `tests/rubino_downloader_bot.py` | 0.7–9 KB | scripts against real accounts; `local_bot_test.py` contains a **hard-coded bot token** (tracked in git history) | move to `examples/` (sanitized) or `tests/integration/` behind `RUBIGRAM_INTEGRATION=1`; the bot token must be treated as leaked and revoked by the owner |
| `E:\Codes\rubigram` (outside the repo) | | an older clone that `pip` has installed in editable mode (`rubigram 0.1.0 E:\Codes\rubigram`) | not touched; `import rubigram` from any directory other than this repo resolves to that stale copy. Recommend `pip install -e C:\Codes\rubigram` after the redesign |

## 7. Sessions and what depends on them

Schema (columns only): `id, api_version, api_url, api_urls_json,
[suggested_urls_json], storages_json, cdn_urls_json, sockets_json, auth,
tmp_session, public_key, private_key_pem, user_guid, updates_state,
device_hash, registered_device, registered_device_version, [bot_token,
bot_offset_id], created_at, updated_at` plus a `meta(key, value)` table with
`version = 1`.

| Session file | Schema | Contents (flags only) | Used by |
|---|---|---|---|
| `my_account.session` | oldest (no `bot_token`, no `suggested_urls_json`) | real user auth + private key + user guid, device registered | `tests/local_test.py` (AI reply bot), `examples/get_rubino_post.py` |
| `test_client.session` | newest | real user auth + private key + user guid, device registered | `tests/local_client_test.py`, `tests/rubino_downloader_bot.py` |
| `local_bot.session` | with bot columns | bot token only | (commented-out code in `tests/local_bot_test.py`) |
| `my_bot.session` | newest | bot token + private key + DC lists | none found |
| `new_me_bot.session` | with bot columns | bot token + private key + DC lists | `tests/local_bot_test.py` |
| `rubino_downloader_bot.session` | newest | bot token only | none found (the script of the same name uses `test_client`) |

`my_account.session` is the proof that old files must keep loading: the
redesigned `FileStorage` must migrate the pre-`bot_token` schema
automatically (the current `FileStorage.open` already ALTERs missing columns).

## 8. Behaviour differences and bugs spotted while reading (to confirm in Phase 1)

- `Sticker._parse` crashes on every sticker (see section 2); the update listener dies.
- `Avatar.download()` does not exist although documented.
- `RpcError.raw` is the encrypted envelope, so `client_show_message` is lost.
- `map_rpc_error` is substring-based; `INVALID_AUTH` → `AuthKeyInvalid` works by
  accident, `NOT_REGISTERED` → `RegisterDeviceRequired` is right, but any
  status containing "code" and "invalid" becomes `CodeIsInvalid`.
- `Client.__enter__` uses `asyncio.run`, which breaks inside any running loop.
- `MemoryStorage.open()` discards state (breaks `set_auth` before `start`).
- `_update_listener_loop` swallows only `TransportError/NetworkError/DecodeError`;
  any parse error stops updates permanently (`log.exception`, then `idle()` returns).
- `SocketTransport` never reconnects by itself; `_ensure_socket_handshake` is
  called before every authenticated RPC (an extra await per call) but only
  re-handshakes when the heartbeat task is gone.
- `RpcTransport` retries only on connection errors / 5xx, once per URL, with no
  backoff; `TOO_REQUESTS` is raised immediately without `retry_after`.
- `UploadTransport.upload_file` reads the entire file into memory.
- `DownloadTransport` builds the URL as `messenger{dc_id}.iranlms.ir`; the
  `storages`/`default_cdn_urls` from `getDCs` are stored but never used.
- Headers: RPC/WS header sets differ from a real Chrome profile (no
  `sec-ch-ua*`); the WS connect sends no extra headers at all after `501cfc8`.
- `getDCs` client info is hard-coded separately from `Client` constants.
- `generate_tmp_session` uses `random`, not `secrets`.
- `Client.download_file` requires auth even for public CDN files.
- `send_message` requires `rnd` for user sessions (callers must generate it).

## 9. Owner notes preserved from files scheduled for deletion

From `TODO` (Persian, paraphrased): (1) fetch the URL list from
`getdcmess.iranlms.ir` — done; (2) create a `Client` for login and init — done;
(3) idea: a Rubika AI assistant that analyses and imitates people's messaging
style and helps them inside Rubika, built on the rubigram library.
`tests/local_test.py` is a prototype of that idea (an OpenAI-compatible
chat completion bot answering questions about the project).

## 10. Environment

Python 3.14.3, pytest 9.0.2, httpx 0.28.1, websockets 16.0, cryptography
46.0.5. `ruff 0.16.6`, `pyright 1.1.411`, `build 1.6.0` were installed for the
quality bar. `graphify` is not installed, so the graph rule does not apply.
`core.autocrlf=true` on this machine, which is why the rescued diff shows
whole-file line-ending churn.
