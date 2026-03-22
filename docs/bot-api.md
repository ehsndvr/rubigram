# Bot API

Rubika Bot API is available through the same `Client` class by passing `token=...`.

## Main Entry Point

```python
from rubigram import Client
from rubigram.bot.types import Button, Keypad, KeypadRow
```

## Example

```python
import asyncio

from rubigram import Client
from rubigram.bot.types import Button, Keypad, KeypadRow

app = Client("my_bot", token="your-bot-token")


@app.on_message()
async def handle_message(client, message):
    await message.reply("received")


async def main():
    await app.send_message(
        "chat-id",
        text="Welcome",
        inline_keypad=Keypad(
            rows=[
                KeypadRow(
                    buttons=[
                        Button(id="100", type="Simple", button_text="Open"),
                    ]
                )
            ]
        ),
    )
    await app.start_polling()
    await app.idle()


if __name__ == "__main__":
    asyncio.run(main())
```

## Implemented Methods

- `get_me()`
- `send_message()`
- `send_poll()`
- `send_location()`
- `send_contact()`
- `get_chat()`
- `get_updates()`
- `forward_message()`
- `edit_message_text()`
- `edit_message_keypad()`
- `edit_inline_keypad()`
- `delete_message()`
- `set_commands()`
- `update_bot_endpoints()`
- `edit_chat_keypad()`
- `get_file()`
- `request_send_file()`
- `upload_file()`
- `send_file()`
- `send_media()`
- `send_photo()`
- `send_document()`
- `send_voice()`
- `send_video()`
- `send_music()`
- `ban_chat_member()`
- `unban_chat_member()`

## Event Sources

Rubigram supports both documented bot update flows:

- long polling through `get_updates()`
- webhook payload parsing through `parse_webhook_update()` and `dispatch_webhook_update()`

Webhook payloads are parsed into `WebhookUpdate`, `Update`, and `InlineMessage` typed objects.

## Filters

Bot handlers use the same filter system:

- `filters.text`
- `filters.private`
- `filters.command("start")`

Example:

```python
@app.on_message(filters.command(["start", "help"]))
async def handle_command(client, message):
    print(message.command)
```
