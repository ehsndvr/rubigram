# rubigram

Async Python client for [Rubika](https://rubika.ir): phone-number sessions,
bots and Rubino, with typed results, composable filters and a pyrogram-style
handler API. The wire protocol follows the official web client (4.4.34):
encrypted HTTPS envelopes, DC discovery and rotation, the retry ladder, socket
pushes with keep-alive and reconnect, chunked uploads and ranged downloads.

```bash
pip install rubigram
```

## A user session

```python
from rubigram import Client, filters

app = Client("my_account")  # session stored in ./my_account.session


@app.on_message(filters.text & filters.private & ~filters.me)
async def echo(client, message):
    await message.reply(f"you said: {message.text}")


app.run()  # first run asks for the phone number and code
```

```python
async with Client("my_account") as app:
    me = await app.get_me()
    page = await app.get_chats()
    sent = await app.send_message("u0…", "**hello**", parse_mode="markdown")
    await app.send_photo("g0…", "pic.jpg", text="caption")
    path = await sent.message.download() if sent.message.file_inline else None
```

## A bot

```python
import os
from rubigram import Client, filters

bot = Client("my_bot", token=os.environ["RUBIGRAM_BOT_TOKEN"])


@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hi!")


bot.run()
```

The same `Client` class serves both; shared methods (`send_message`,
`send_photo`, `get_me`, `get_updates`, …) switch to the Bot API automatically.

## Highlights

- **Typed results** for every documented method (`UserInfo`, `Chat`, `Message`,
  `GroupInfo`, …) with bound helpers: `message.reply()`, `message.delete()`,
  `message.forward()`, `message.react()`, `message.download()`, `chat.mute()`.
  Unknown keys stay reachable through `.extra`.
- **All 203 web-client RPCs** as raw methods (`rubigram.raw.methods`) plus
  `invoke_raw("anyMethod", {...})`.
- **Updates over the socket or by polling**: `Transport.WS` (default) keeps a
  socket with the web client's heartbeat and reconnect rules; `Transport.HTTP`
  polls `getChatsUpdates`. Switch with `set_transport()` / `use_transport()`.
- **Handlers and filters**: `on_message`, `on_edited_message`,
  `on_deleted_message`, `on_chat_update`, `on_activity`, `on_notification`,
  `on_callback_query`, `on_raw_update`; groups, `StopPropagation`,
  `ContinuePropagation`; sync or async filters composed with `& | ~`.
- **Exact errors**: one exception class per server `status_det`
  (`InvalidInput`, `InvalidAuth`, `NotRegistered`, `TooRequests.retry_after`, …)
  with the server's `client_show_message`.
- **Sessions** in SQLite, in memory or as a portable string
  (`export_session_string()` / `Client.from_session_string()`), migrated from
  0.1 automatically.
- **Configurable networking**: timeout, retry policy, proxy, user agent, DC
  URLs; `pip install rubigram[socks]` for SOCKS proxies.
- **Rubino**: fetch and download posts and stories shared into chats.

## Documentation

- [Overview](docs/overview.md) — concepts and package map
- [Authentication and sessions](docs/authentication.md)
- [Transports](docs/transports.md) — WS vs HTTP, retries, proxy, uploads
- [Updates and handlers](docs/updates-and-handlers.md) — decorators, filters, dispatcher
- [Method reference](docs/method-reference.md) — every method with `[HTTP]`/`[WS]`/`[both]`/`[bot]` tags
- [Bot API](docs/bot-api.md)
- [Rubino](docs/rubino.md)
- [Examples](docs/examples.md) and the [`examples/`](examples) directory
- [Architecture](docs/architecture.md) — how the layers fit together
- [Migrating from 0.1](docs/migration.md)
- [Membership worker](docs/membership-worker.md) — the Django + Celery service that runs join/leave/view orders for a panel
- [Redesign notes](docs/redesign) — protocol audit, coverage matrix, decisions

## Membership worker

`membership_worker/` is a deployable service built on the library: it keeps a
pool of Rubika accounts (session strings in its database) and executes
join / leave / view orders received over a signed HTTP API, reporting back with
signed callbacks. It speaks the same protocol as the balegram worker, so the
same panel drives both. See [docs/membership-worker.md](docs/membership-worker.md)
and, for hosting it, [deploy/dokploy/README.md](deploy/dokploy/README.md).

## Development

```bash
pip install -e .[dev]
python -m pytest -q          # 100% offline: an in-process fake Rubika answers every call
ruff check . && ruff format --check .
pyright
python tools/gen_method_reference.py   # after changing docstrings
```

Live checks against the real servers are opt-in: `RUBIGRAM_INTEGRATION=1`
(see [docs/examples.md](docs/examples.md#live-tests)).

## Status and limits

- Protocol facts come from the web client bundle and public discovery; a few
  response shapes could not be observed live and are typed permissively
  (marked in the method reference and in `docs/redesign/01-coverage-matrix.md`).
- Sending RPCs over the socket is not implemented (the web client does not do it
  either); voice/video call signalling is exposed only at the raw level.
- Python 3.10+.

## License

LGPL-2.1-or-later. See [LICENSE](LICENSE).
