# Architecture

rubigram follows the layered layout of the author's `balegram` library: a
thin client composed of domain mixins on top of a transport layer, a raw
method layer, typed results and a handler/dispatcher pair. Nothing is copied
from balegram; the pattern is re-implemented for Rubika's protocol.

## Package tree

```
rubigram/
├── __init__.py            public surface: Client, Transport, RetryPolicy, Peer, errors, handlers, namespaces
├── client/
│   ├── client.py          Client: construction, start/stop/run, transports, handler decorators
│   ├── base.py            BaseClient: attributes and cross-mixin hooks every mixin can rely on
│   └── methods/           one mixin per domain (advanced, auth, sessions, users, chats, messages,
│                          media, groups, channels, join_links, stickers, settings, services,
│                          rubino, bot_api, updates) aggregated by Methods
├── handlers/              Handler kinds, Dispatcher, StopPropagation / ContinuePropagation
├── filters/               Filter class, built-in filters, factories (regex, command, chat, user, button_id)
├── types/                 Object base + generic parser; files, user, message, chat, group, channel,
│                          update, settings, stickers, rubino; bot/ for Bot API payloads
├── raw/
│   ├── base.py            RawMethod[ResultT]: method_name, auth_mode, dc_type, api_version, retries, result
│   ├── methods/           every web-client RPC grouped by domain + METHODS registry
│   └── functions/         envelope/client blocks, message metadata (markdown/html), file_inline, updated_parameters
├── network/               transport_mode (Transport), retry (RetryPolicy), pool (UrlPool), headers,
│                          discovery (DcDiscovery, DcRepository), http (HttpTransport, JsonTransport),
│                          ws (SocketTransport), upload, download, bot_api (BotTransport)
├── storage/               Storage ABC + FIELDS registry, SqliteStorage, MemoryStorage, session string codec
├── crypto/                cipher (AES-CBC, caesar, passphrase), auth (RSA sign/unwrap, key export), codec
├── errors/                exception hierarchy, status_det mapping, raise_for_status
├── enums/                 server enumerations
├── utils/                 phone numbers, random ids, device hash, OGG duration
└── bot/, exceptions/, types/results.py, network/transport.py, network/socket.py   deprecated import shims
```

Every module stays under ~450 lines and has one responsibility.

## Request path

```
client.get_user_info("u0…")
  → Users.get_user_info builds raw.methods.GetUserInfo(user_guid=…)
  → Advanced.invoke(method)
      auth_mode "auth"  → _call_rpc: ensure registerDevice, build data object
                          {method, input, client}, encrypt with the session
                          auth (Codec.build_payload), POST via HttpTransport
                          (retry ladder + DC rotation), decrypt, raise_for_status,
                          NOT_REGISTERED → registerDevice once and retry
      auth_mode "tmp"   → same with the tmp_session envelope (login flow)
      auth_mode "none"  → _call_service: plain JSON {method, api_version, data,
                          auth, client(PWA)} to a service URL or the DC pool
                          (getBaseInfo, Rubino, web apps)
  → method.parse_response(client, data) → UserInfo
```

`RawMethod` subclasses are dataclasses: fields serialize to `input`
automatically (None dropped, enums to values, nested models to dicts), and the
class attributes decide the envelope (`auth_mode`), the DC pool (`dc_type`),
the `api_version`, the retry count and the result model. `invoke_raw()` creates
such a class on the fly.

## Update path

```
SocketTransport (handshake, {} ping 30 s after the last frame, reconnect after
20 s of silence or a close, rotating socket URLs)
  → frames with type "messenger" and data_enc
  → UpdatesMixin.receive_update decrypts with the session auth → types.Updates
  → Dispatcher.dispatch_updates:
        raw → message_updates by action (New/Edit/Delete) → chat_updates
        → show_activities → show_notifications → draft_message_updates
  → handlers by group; filters evaluated (sync or async); Stop/ContinuePropagation
```

`Transport.HTTP` replaces the socket with `getChatsUpdates` polling and
synthesises message events from new `last_message` entries. Bots poll
`getUpdates` (`dispatch_bot_update`) or receive webhook bodies
(`dispatch_webhook_update`). The listener task starts only when handlers are
registered (or `idle()` is called), so plain scripts never poll in the
background.

## Mixins and BaseClient

`Client(Methods)` where `Methods` aggregates the mixins. Each mixin derives from
`BaseClient`, which declares the attributes the constructor sets and the few
hooks mixins call on each other (`invoke`, `_finalize_login`,
`_ensure_socket`, `_bot_send_message`, …) as typed stubs. This keeps every
mixin type-checkable on its own without circular inheritance; the stubs are
overridden by the real implementations earlier in the MRO and never run.

## Types

`types.Object` is a keyword-only dataclass base whose parser is driven by type
hints: nested models, lists of models, optionals and forward references across
modules are resolved once per class and cached. Unknown keys go to `.extra`
and, when the name is free, become attributes; properties are never
overwritten. `__post_parse__` hooks derive fields (for example
`Chat.type` from `abs_object` or the guid prefix, `MessageUpdate` syncing
envelope fields into its `Message`). Models keep a private client reference
for bound helpers.

## Storage

`Storage` declares its fields once (`FIELDS`) and exposes typed accessors;
`SqliteStorage` adds missing columns on open and bumps `meta.version`,
`MemoryStorage` keeps state across close/open. The session string is
`rbg2.` + CRC32 + zlib + base64url of the session dict (the 0.1 plain format is
still readable).

## Errors

`errors.mapping` turns `(status, status_det, payload)` into the exact class;
`RpcError` keeps the decrypted payload, the method name and the server's
`client_show_message`. Transport-level failures raise `NetworkError` /
`RequestTimeout` after the retry ladder.

## Tests

`tests/fake_rubika.py` is an in-process Rubika: it decrypts the client's
envelopes with the same AES scheme, records `(method, input)` and answers from
fixtures (`tests/fixtures/rubika/*.json`, sanitized recordings) or from a table
of canned responses, including inner and outer error envelopes. Transports are
swapped by monkeypatching the names `Client` imports, so the real
`HttpTransport`, `SocketTransport`, upload and download code paths are covered
separately with `httpx.MockTransport` and a stub websockets module in
`tests/test_network.py`. No test opens a network connection; live checks are
opt-in under `tests/integration/`.

## Quality gates

`ruff check`, `ruff format --check`, `pyright` (basic) and `pytest` must pass;
`python -m build` produces a wheel that contains only the `rubigram` package.
`tools/gen_method_reference.py` regenerates the method reference from the
docstrings, which carry the `[HTTP]` / `[WS]` / `[both]` / `[bot]` tags.
