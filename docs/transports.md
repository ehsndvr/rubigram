# Transports

Rubika's web protocol sends **every RPC over HTTPS** as an encrypted envelope.
The WebSocket carries only the handshake, a `{}` heartbeat and server pushes.
So in rubigram the transport mode does not change how a call is sent; it
decides **how updates reach you** and whether a socket is kept open.

| Mode | RPC calls | Updates | Socket |
|---|---|---|---|
| `Transport.WS` (default) | HTTPS | pushed by the server, decrypted and dispatched to handlers | opened after login, kept alive with a `{}` ping 30 s after the last frame, reconnected after 20 s of silence or a close |
| `Transport.HTTP` | HTTPS | `get_updates()` → `getChatsUpdates`; the background loop turns new `last_message` entries into message events | never opened |

Bot sessions (`Client(token=...)`) always use Bot API long polling (`getUpdates`)
or webhooks; the mode is ignored.

## Choosing the mode

```python
from rubigram import Client, Transport

app = Client("my_account", transport="http")   # or Transport.HTTP
app.set_transport(Transport.WS)                 # switch at runtime

async with app.use_transport("http"):           # temporarily
    updates = await app.get_updates()           # polls getChatsUpdates

updates = await app.get_updates(transport="ws") # per call: waits for one pushed frame
```

`get_updates()` returns a `ChatsUpdates` in HTTP mode and a decrypted
`Updates` frame in WS mode. `receive_update()` always waits for a pushed frame
and opens the socket if needed. The method reference tags every method with
`[HTTP]`, `[WS]`, `[both]` or `[bot]`.

## Discovery and DC rotation

On start the client fetches `getDCs` (`api_version 4`) from
`https://getdcmess.iranlms.ir/`, stores the API, socket, storage and CDN URLs
in the session and after login refreshes `getBaseInfo` (services base) for the
Rubino and wallet hosts. `DcRepository` (`client.dc`) exposes them:

```python
app.dc.api_urls            # ["https://messengerg2c…", …]
app.dc.storage_url(491)    # "https://messanger491.iranlms.ir/GetFile.ashx"
app.dc.urls("rubino")
```

Failed requests rotate to the next API URL before each retry; when every URL
failed once, `getDCs` is fetched again.

## Retries and timeouts

`RetryPolicy(delays=(0, 2, 3, 5, 10), timeout=20)` mirrors the web client:
five attempts with growing delays, 20 s per request. Override it globally or
per call:

```python
from rubigram import Client, RetryPolicy

app = Client("me", timeout=30, retry_policy=RetryPolicy(delays=(0, 1, 2), timeout=30))
await app.get_chats()                                   # policy of the client
await app.invoke(raw.methods.GetChats(), retries=0)     # never retry (try_count 0)
```

`sendChatActivity` and a few other fire-and-forget methods declare
`retries = 0` themselves. Retried statuses: network errors, timeouts, HTTP 5xx
and undecodable bodies. HTTP 4xx and every RPC error are raised immediately.

## Proxy and user agent

```python
app = Client("me", proxy="http://127.0.0.1:8080", user_agent="Mozilla/5.0 …")
```

The proxy reaches the API, discovery, upload/download and socket transports
(SOCKS proxies need `pip install rubigram[socks]` and websockets ≥ 15). The
user agent is used for every HTTPS request, the socket handshake and the
`device_hash` sent by `registerDevice`.

## Uploads and downloads

Uploads go to the `upload_url` returned by `requestSendFile`, in 131072-byte
parts with the `auth`, `file-id`, `access-hash-send`, `part-number`,
`total-part` and `chunk-size` headers; each part uses the retry policy.
Downloads POST to the storage of the file's `dc_id` with `start-index`/`last-index`
ranges and honour the `total_length` header. Both accept a `progress(current,
total, *progress_args)` callback and can return bytes (`in_memory=True`).

## Low-level access

```python
from rubigram import raw

user = await app.invoke(raw.methods.GetUserInfo(user_guid="u0…"))   # typed result
anything = await app.invoke_raw("getChatAds", {"state": 0})           # RawObject
```

`invoke()` builds the `{api_version, auth, data_enc, sign}` envelope, decrypts
the answer, maps `status_det` to an exception and registers the device once
when the server answers `NOT_REGISTERED`. Login methods (`sendCode`,
`signIn`) use the `tmp_session` form of the envelope automatically.
