# Overview

rubigram talks to Rubika the way the official web client does and wraps the
result in a small, typed, async API. This page introduces the concepts; the
other pages go deeper.

## The client

`rubigram.Client` is one class with two personalities:

```python
Client("my_account")                  # phone-number session (user API)
Client("my_bot", token="…")           # Bot API (botapi.rubika.ir)
```

`start()` opens the session storage, discovers the data centres, logs in when
needed, registers the device and, in `Transport.WS` mode, opens the socket.
`stop()` closes everything. `run()` and `async with client:` wrap both.
Methods are grouped into mixins by domain (users, chats, messages, media,
groups, channels, join links, stickers, settings, services, Rubino, bot API,
updates) and are all listed in [method-reference.md](method-reference.md).

Every `object_guid` argument accepts a guid string, a `rubigram.Peer`, or any
typed object that carries a guid (a `Chat`, a `User`, a `Message`), and most
methods also take `peer=`.

## Sessions

A session is the `auth` key plus the login key pair, the user guid, the
device registration state, the DC configuration and update states. It lives in
`name.session` (SQLite) by default, in memory with `in_memory=True`, or as a
portable string. See [authentication.md](authentication.md).

## Requests

Every user-API call is an encrypted HTTPS POST:

```
{"api_version": "6", "auth": caesar(auth), "data_enc": AES(json), "sign": RSA(data_enc)}
```

`Client.invoke(raw_method)` builds it, sends it through the retry ladder with
DC rotation, decrypts the answer and maps `status_det` to an exception. Typed
methods are thin wrappers around `invoke()`; `invoke_raw(name, input)` calls
anything by name. Bot API calls are plain JSON POSTs to
`https://botapi.rubika.ir/v3/<token>/<method>`.

## Results

Responses become dataclass models from `rubigram.types` (`UserInfo`, `Chat`,
`Message`, `GroupInfo`, `SentMessage`, …). Unknown keys are kept in `.extra`
and as attributes, so a server change never breaks parsing. Models carry a
reference to the client, which powers helpers such as `message.reply()`,
`message.download()`, `user.block()`, `chat.mute()` or `group.leave()`. `to_dict()` and
`str()` give plain data back.

## Updates

In `Transport.WS` mode the server pushes encrypted frames over the socket;
rubigram decrypts them into `Updates` objects and dispatches
`message_updates`, `chat_updates`, `show_activities`, `show_notifications`
and `draft_message_updates` to the registered handlers. In `Transport.HTTP`
mode `getChatsUpdates` is polled instead. Bots poll `getUpdates` or receive
webhooks. See [updates-and-handlers.md](updates-and-handlers.md) and
[transports.md](transports.md).

## Errors

All exceptions derive from `rubigram.errors.RubigramError`:

| Class | When |
|---|---|
| `NetworkError`, `RequestTimeout` | connection problems after the retry ladder |
| `DecodeError` | undecryptable or malformed answers |
| `AuthError`, `LoginRequired`, `TmpSessionRequired`, `SessionExpired` | no or invalid session for the call |
| `RpcError` and subclasses (`InvalidInput`, `InvalidAuth`, `NotRegistered`, `TooRequests`, `UsernameExists`, `CodeIsInvalid`, …) | the server refused the call; `.status`, `.status_det`, `.client_show_message`, `.raw` |
| `BotApiError` | Bot API answers with `status != OK` |
| `StorageError` | session storage problems |

`TooRequests.retry_after` parses the wait time from the server message
(Persian and English). `InvalidAuth.is_session_dead` tells whether the session
must be recreated.

## Package map

| Package | Role |
|---|---|
| `rubigram.client` | `Client`, `BaseClient`, the method mixins |
| `rubigram.handlers`, `rubigram.filters` | dispatcher, handler kinds, filters |
| `rubigram.types` | result models (user API) and `rubigram.types.bot` |
| `rubigram.raw` | `RawMethod` base, every RPC class, payload builders |
| `rubigram.network` | HTTP/JSON/socket/upload/download/bot transports, retry policy, DC discovery |
| `rubigram.storage` | `Storage` ABC, SQLite and memory storages, session string codec |
| `rubigram.crypto` | AES-CBC envelope cipher, caesar auth encoding, RSA signing and unwrapping |
| `rubigram.errors` | exception hierarchy and the `status_det` mapping |
| `rubigram.enums` | server enumerations (chat types, actions, admin rights, bot keypads) |
| `rubigram.utils` | phone normalisation, ids, OGG duration |

Compatibility shims for rubigram 0.1 import paths are listed in
[migration.md](migration.md).
