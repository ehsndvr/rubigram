# Rubigram

Raw-first Rubika client library for Python.

Current status:
- login/session/device flow implemented
- HTTP RPC implemented
- websocket updates implemented
- typed result models implemented for core methods
- callback system with `@app.on_message(...)` implemented
- composable filters implemented

## Quick Example

```python
import asyncio
from rubigram import Client, filters

app = Client("my_account")


@app.on_message(filters.text & filters.private & ~filters.me)
async def handle_message(client, message):
    print(message.text)
    await message.reply("received")


async def main():
    await app.start()
    await app.idle()


if __name__ == "__main__":
    asyncio.run(main())
```

## Docs

- [Client Methods Reference](docs/client-methods.md)
- [Update Message Types](docs/update-message-types.md)

## Current Public Surface

Main imports:

```python
from rubigram import Client, filters, raw, types
```

Examples:
- `await app.get_me()`
- `await app.send_message(...)`
- `await app.send_photo(...)`
- `await app.send_document(...)`
- `await app.get_chats_updates()`
- `await app.receive_socket_update()`
- `@app.on_message(filters.text)`

Bot API:
- `app = Client("my_bot", token="...")`
- `await app.get_me()`
- `await app.send_message("chat_id", text="hello")`
- `await app.start_polling()`
- `@app.on_message(filters.command("start"))`

## Notes

Methods that still return `RawObject` are implemented but not yet fully promoted to a dedicated typed model.

Most peer-aware methods accept either the legacy `object_guid` string or a `peer=` value such as `rubigram.Peer("u0...")` or a bound typed object carrying `object_guid` / `user_guid`.
For bot accounts, use the same `Client` class with `token=...`; the token is persisted in the same session storage and session string.
