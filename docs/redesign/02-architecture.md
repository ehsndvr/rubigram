# Phase 2 — architecture plan

Decided 2026-09-07 after the audit (00) and the protocol discovery (01). This
is the contract for Phase 3; every deviation must be recorded here.

## 1. Target package tree

```
rubigram/
  __init__.py            Client, Transport, filters, handlers, types, errors, raw, enums, Peer, __version__
  version.py             0.2.0
  peer.py                Peer (unchanged public API)
  client/
    __init__.py
    client.py            thin Client: constructor, lifecycle, storage/transport wiring, invoke seam
    methods/
      __init__.py        Methods = all mixins
      auth.py            send_code, sign_in, sign_up, login, register_device, logout, get_time
      users.py           me/profile/username/block/contacts/common groups/profile links
      chats.py           dialogs, chats-by-id, abs objects, seen, chat actions, delete chats, ads, spam, report
      groups.py          group info/members/admins/access/links/join/leave/owner transfer
      channels.py        channel info/members/admins/link/username/join/leave
      join_links.py      join links and join requests
      messages.py        send/edit/delete/forward/get/search/pin/activity/read participants/transcription
      reactions.py       reactions and polls
      media.py           request_send_file, upload/download, send_* media, avatars, wallpapers
      stickers.py        sticker sets, gif set, send_sticker
      folders.py         chat folders
      drafts.py          drafts
      settings.py        privacy, user/appearance settings, two-step, phone change, delete account
      sessions.py        sessions + session string export/import
      search.py          search_global_objects
      bots.py            user-side bot interaction (getBotInfo, stopBot, selections, sendMessageAPICall)
      bot_api.py         token-mode Bot API (botapi.rubika.ir/v3)
      services.py        services, web apps, links, barcodes, map, wallet, payments
      live.py            live methods
      voice_chats.py     group voice chat methods
      rubino.py          get_rubino_post, get_rubino_stories, send_rubino_post, get_base_info
      updates.py         get_updates, receive_update, run/idle, polling loops
      advanced.py        invoke, invoke_raw, _call_rpc seam, peer/guid resolution, formatting glue
  handlers/
    __init__.py          Handler classes, StopPropagation, ContinuePropagation
    handler.py           Handler base (callback + filter, sync or async)
    message_handler.py   MessageHandler, EditedMessageHandler, DeletedMessageHandler
    chat_update_handler.py, activity_handler.py, notification_handler.py, raw_update_handler.py
    inline_message_handler.py, callback_query_handler.py   (bot)
    dispatcher.py        groups, ordering, propagation control, update fan-out
  filters/
    __init__.py, filters.py   Filter base with & | ~, sync/async, all built-ins, factories
  errors/
    __init__.py, exceptions.py, mapping.py
  exceptions/__init__.py     deprecated re-export shim of rubigram.errors
  raw/
    __init__.py, base.py     RawMethod (generic dataclass → input serialization)
    functions/               payload builders with logic (metadata, file_inline, updated_parameters, envelopes)
    methods/                 declarative RPC classes per domain (auth, users, chats, groups, channels, messages,
                             files, stickers, folders, settings, sessions, bots, services, live, voice_chats, rubino)
  network/
    transport_mode.py        Transport enum + coerce
    retry.py                 RetryPolicy (delays ladder, per-call override)
    pool.py                  UrlPool (per DcType rotation with switch lock)
    discovery.py             DcDiscovery (getDCs/getBaseInfo) + DcRepository
    http.py                  HttpTransport (encrypted RPC) + JsonTransport (plain JSON)
    ws.py                    SocketTransport (handshake, idle ping, silence detection, reconnect)
    upload.py, download.py   chunked file transfer with progress, retries, storages map
    headers.py               browser profile (configurable user agent, sec-ch-ua)
    bot_api.py               BotTransport
  crypto/                    auth.py, cipher.py, codec.py (unchanged algorithms)
  storage/
    base.py                  Storage ABC + field registry
    sqlite.py                SqliteStorage (file) with versioned migrations; FileStorage alias
    memory.py                MemoryStorage (dict, reopen-safe)
    session_codec.py         versioned portable session string (legacy format still readable)
  types/
    object.py, raw_object.py, files.py, user.py, chat.py, message.py, group.py, channel.py,
    update.py, settings.py, stickers.py, folders.py, rubino.py, formatting.py, bot/ (keypad, message, update)
  enums/                     existing + DcType, ChatType, MessageType, ActivityType, ChatAction, ...
  utils/                     helpers (ids, phone normalizer, markdown/html parser, ogg duration)
  bot/                       deprecated shim package: re-exports types/enums only (BotClient removed)
```

Everything under `rubigram/methods/`, `rubigram/session/`, `rubigram/types/user_and_chats/`,
`rubigram/crypto/encryption.py`, `rubigram/types/results.py` and `rubigram/bot/client.py`
disappears; `rubigram/client.py` becomes a one-line re-export.

## 2. Decisions

### Bot API: one `Client`
`Client("my_bot", token="…")` is the only bot entry point. Mode is detected from
the token (constructor or stored in the session). Bot methods live in
`client/methods/bot_api.py`, the transport in `network/bot_api.py`, the types in
`types/bot/`. `BotClient` is deleted. Reasons: the two implementations had
already diverged (polling loop, dispatch, error unwrapping), the session
storage and session string already carry the token, handlers/filters/dispatcher
are shared, and the owner's own scripts only ever used `Client(token=…)`.
`rubigram.bot.types` / `rubigram.bot.enums` remain as deprecated import shims so
`from rubigram.bot.types import Keypad` keeps working with a `DeprecationWarning`.

### Transports (adapted to Rubika)
Rubika's web protocol carries **every RPC over HTTPS**; the WebSocket carries
only `handShake`, the `{}` ping and server pushes (`type: "messenger"` frames).
That is different from Bale, where the socket is an RPC channel. The transport
selector therefore controls *how the client stays connected and receives
updates*, not how a single RPC is sent:

| Mode | RPCs | Updates | Socket |
|---|---|---|---|
| `Transport.WS` (default) | HTTPS | pushed over the socket, dispatched to handlers | opened after login, kept alive, auto-reconnect |
| `Transport.HTTP` | HTTPS | `get_updates()` polling (`getChatsUpdates` + `getMessagesUpdates`), also dispatched to handlers by `run()`/`idle()` | never opened |

API surface identical to balegram: `Client(..., transport="ws"|"http")`,
`client.transport`, `set_transport()`, `async with client.use_transport()`,
and a per-call `transport=` on the update-side methods (`get_updates`,
`receive_update`, `idle`). Unary RPC methods do not take `transport=` because
there is nothing to choose; the method reference tags them `[HTTP]`, the
update methods `[both]` or `[WS]`, bot methods `[bot]`. Sending RPCs over the
socket is not implemented because the server's response correlation could not
be observed; `raw` keeps the door open (`Client.send_socket_frame`).

### Raw layer
`RawMethod` becomes a generic dataclass base: fields are serialized to
`input` automatically (None dropped, enums to values, nested models to dicts),
so a raw method is ~6 lines (`method_name`, fields, `result` type, optional
`auth_mode`). `raw/functions/` holds the builders that need logic (message
metadata from parse modes, `file_inline`, `updated_parameters` computation,
envelope construction). `rubigram.raw.methods` keeps every existing class name.
`Client.invoke_raw("methodName", {...})` calls any method, implemented or not,
and returns a `RawObject`.

### Types
One `Object` base with a generic parser driven by dataclass type hints:
nested models, lists of models, optional fields, unknown keys preserved both
as attributes and in `.extra`. Bound methods stay (`message.reply()`,
`message.delete()`, `message.forward()`, `message.react()`, `message.pin()`,
`message.download()`, `user.block()`, `group.leave()`, `avatar.download()`).
`results.py` is split by domain; all names stay importable from
`rubigram.types`. The bug in `Sticker._parse` and the misplaced
`Avatar.download` are fixed by construction. `MessageUpdate`/`ChatUpdate`
merge with their `Socket*` twins (the socket names stay as aliases).

### Errors
`RubigramError` (alias `RubikaError`) → `TransportError`/`NetworkError`,
`DecodeError`, `StorageError`, `AuthError` (`LoginRequired`, `SessionExpired`),
`RpcError(status, status_det, raw, method, client_show_message)` with one
subclass per `status_det` seen in the web client (`InvalidInput`,
`NotSupportedApiVersion`, `ServerError`, `InvalidMethod`, `CodeIsUsed`,
`CodeIsExpired`, `InvalidAuth` (alias `AuthKeyInvalid`), `NotRegistered`
(alias `RegisterDeviceRequired`), `TooRequests` (`retry_after`), `UsernameExists`,
`Undeliverable`), plus `BotApiError`. Mapping is exact on `status_det`, with
`status` deciding `InvalidAuth` severity (`ERROR_ACTION` = session dead). The
old substring heuristics and the `PhoneCodeInvalid`/`PhoneHashInvalid`/
`CodeIsInvalid` names are kept as aliases raised for the matching
`client_show_message`/method combinations so existing `except` clauses work.
`rubigram.exceptions` re-exports everything with a `DeprecationWarning`.

### Network
- `RetryPolicy(delays=(0, 2, 3, 5, 10), timeout=20)`: the web client's ladder;
  DC URL rotates before each retry; a fresh `getDCs` is fetched once when all
  URLs failed; `retries=`/`timeout=` per call; `try_count=0` semantics via
  `retries=0`.
- `SocketTransport`: connect → handshake → reader task; ping `{}` 30 s after the
  last frame; reconnect when 20 s pass without a frame after a ping, or on
  close after 5 s, rotating socket URLs; re-handshake automatically; incoming
  frames go through a queue and a callback; proxy and user agent configurable.
- `DcRepository`: `getDCs` payload + `getBaseInfo` suggested URLs, persisted in
  storage, `urls(DcType)`, `storage_url(dc_id)` for downloads, `cdn_urls(tag)`.
- Downloads use `storages[dc_id]`; uploads stream from disk in 131072-byte
  chunks with the retry ladder.
- `proxy=` and `user_agent=` on the client reach every transport (httpx and
  websockets ≥ 15; older websockets without proxy support raise).

### Storage and session string
`Storage` ABC with a declared field list; `SqliteStorage` (file; `FileStorage`
alias) migrates any older schema by adding missing columns and bumping
`meta.version`; `MemoryStorage` is dict-based and survives close/open.
Session string v2: `rbg2.` + base64url(zlib(JSON)) + CRC32; the old prefix-less
base64url JSON is still accepted. `Client.from_session_string()` and
`export_session_string()` as in balegram.

### Client, handlers, filters
`Client` keeps: `start/stop/run/idle`, `authorize` (now `login()` with
`code_callback`; the interactive prompt is a default callback used only when
stdin is a TTY), `invoke`, `on_message`, `on_inline_message`, `download_file`,
`export_session_string`, `receive_socket_update` (deprecated alias of
`receive_update`). New decorators: `on_edited_message`, `on_deleted_message`,
`on_chat_update`, `on_activity`, `on_notification`, `on_callback_query` (bot),
`on_raw_update`; `add_handler/remove_handler` with groups;
`StopPropagation`/`ContinuePropagation`. Filters support sync and async
callables, `&`, `|`, `~`, and cover both user and bot messages.

### Backward compatibility (documented in docs/migration.md)
Imports that keep working: `from rubigram import Client, filters, raw, types, Peer, enums, errors`;
`rubigram.raw.methods.*`; `rubigram.storage.*`; `rubigram.exceptions` (warning);
`rubigram.bot.types` / `rubigram.bot.enums` (warning); `rubigram.client.Client`.
Renamed or corrected methods keep aliases with `DeprecationWarning`:
`get_history` → `get_messages`, `get_chat` → `get_chats_by_id`,
`delete_message` → `delete_messages`, `block_user`/`unblock_user` →
`set_block_user`, `upload_group_avatar`/`set_group_photo` → `upload_avatar`,
`send_uploaded_media` → `send_media`, `receive_socket_update` → `receive_update`,
`start_polling` → `run`/`idle`. Constructor keywords `enable_socket_handshake`,
`interactive_auth`, `socket_heartbeat_interval` keep working.

### Owner-taste decisions taken without asking
1. Licence: LGPL-2.1-or-later, matching balegram.
2. `rubigram-ui/` moves to `tools/payload-decoder/` (developer tool, kept).
3. Real-account scripts move to `examples/` (sanitized) and
   `tests/integration/` (skipped unless `RUBIGRAM_INTEGRATION=1` and a session
   name is given); the hard-coded bot token is removed and reported as leaked.
4. The worktree branch `claude/rubigram-balegram-redesign-80eb77` is kept as the
   redesign branch (rename to `redesign/balegram-parity` at merge time if wanted).
5. Live logged-in observation was not possible; every fact in 01 comes from the
   bundle and the public `getDCs`; unverified response shapes are typed
   permissively (`RawObject` fields) and marked in the method reference.

## 3. Phase 3 order and gates

1. errors → 2. network → 3. storage/session → 4. raw (generic base, builders,
all 204 methods) → 5. types split → 6. client + mixins + bot merge → 7.
handlers/filters/dispatcher → 8. typed results and tests for P0/P1 methods →
9. Rubino mixin → 10. cleanup. Each step ends with `python -m pytest -q` green
and one or more bilingual commits; the old monolithic `tests/test_client.py`
is replaced by per-domain tests using a fake transport as the client is
rewritten.
