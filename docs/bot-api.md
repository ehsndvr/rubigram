# Bot API

Bots use the same `Client` class: pass the token and every shared method
switches to `https://botapi.rubika.ir`.

```python
import os
from rubigram import Client, filters
from rubigram.types.bot import Button, Keypad, KeypadRow

bot = Client("my_bot", token=os.environ["RUBIGRAM_BOT_TOKEN"])

@bot.on_message(filters.command("start"))
async def start(client, message):
    keypad = Keypad(rows=[KeypadRow(buttons=[Button(id="hello", type="Simple", button_text="Say hi")])])
    await message.reply("Welcome!", inline_keypad=keypad)

@bot.on_callback_query(filters.button_id("hello"))
async def pressed(client, message):
    await client.send_message(message.chat_id, "hi!")

bot.run()          # long polling with getUpdates; the offset is stored in the session
```

## Shared methods that switch to the Bot API

| Method | Bot API call |
|---|---|
| `send_message(chat_id, text, chat_keypad=, inline_keypad=, chat_keypad_type=, disable_notification=, reply_to_message_id=)` | `sendMessage` |
| `send_photo` / `send_video` / `send_voice` / `send_music` / `send_gif` / `send_document` / `send_media` | `requestSendFile` → upload → `sendFile` |
| `send_location`, `create_poll` / `send_poll` | `sendLocation`, `sendPoll` |
| `edit_message` / `edit_message_text`, `delete_message`, `forward_message` | `editMessageText`, `deleteMessage`, `forwardMessage` |
| `get_me`, `get_chat` | `getMe`, `getChat` |
| `get_updates` | `getUpdates` |
| `download_file(file_id or File)`, `upload_file(upload_url=, path=)` | `getFile` + download, multipart upload |

Bot-only methods: `send_contact`, `edit_message_keypad`, `edit_chat_keypad`,
`set_commands`, `update_bot_endpoints`, `get_file`, `download_bot_file`,
`upload_bot_file`, `send_file`, `ban_chat_member`, `unban_chat_member`,
`get_bot_updates`, `parse_webhook_update`, `dispatch_webhook_update`.
User-only methods raise `RubigramError` on a bot session, and `invoke()` raises
`TransportError` because Rubika RPCs need a phone session.

`chat_id` values come from updates (`message.chat_id`), never from user guids;
sending to a `u0…` guid answers `INVALID_INPUT` and rubigram adds a hint to the
error.

## Updates

`bot.run()` / `await bot.idle()` poll `getUpdates` and dispatch:

| Update | Handler |
|---|---|
| `NewMessage` | `on_message` (and `on_callback_query` when `aux_data.button_id` is set) |
| `UpdatedMessage` | `on_edited_message` |
| `RemovedMessage` | `on_deleted_message` (receives the `Update`, use `removed_message_id`) |
| inline messages (webhook only) | `on_inline_message` and `on_callback_query` |
| everything | `on_raw_update` |

Webhooks: register the URL once with `update_bot_endpoints(url, "ReceiveUpdate")`
(and `"ReceiveInlineMessage"`), then feed each request body to
`dispatch_webhook_update(payload)` from your web framework. `parse_webhook_update`
only parses.

## Files

```python
sent = await bot.send_photo(chat_id, "pic.jpg", text="caption")
path = await bot.download_file(message.file)          # getFile → download_url
data = await bot.download_file(message.file.file_id, in_memory=True)
```

## Types and enums

Bot payloads are typed in `rubigram.types.bot` (`Message`, `Update`,
`BotUpdates`, `InlineMessage`, `Keypad`, `KeypadRow`, `Button`,
`ButtonSelection`, `ButtonCalendar`, `ButtonNumberPicker`,
`ButtonStringPicker`, `ButtonTextbox`, `ButtonLocation`, `AuxData`, `File`,
`Chat`, `Bot`, `BotCommand`, `Poll`, `SentMessage`, `WebhookUpdate`) with the
enums in `rubigram.enums` (`ButtonType`, `ChatKeypadType`, `UpdateType`,
`FileType`, `MessageSender`, `UpdateEndpointType`, …). Every model accepts
keyword arguments and serializes with `to_dict()`.

Errors: a `{"status": "INVALID_INPUT"}` answer raises the same
`rubigram.errors.InvalidInput` as the user API; other statuses raise
`BotApiError` with the raw payload.
