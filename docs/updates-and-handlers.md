# Updates and handlers

## Registering handlers

```python
from rubigram import Client, filters, StopPropagation

app = Client("my_account")


@app.on_message(filters.text & filters.group)
async def group_text(client, message):
    ...


@app.on_message(filters.command("ping"), group=1)
async def ping(client, message):
    await message.reply("pong")
    raise StopPropagation            # nothing else runs for this update


@app.on_chat_update()
async def chat_changed(client, update):
    print(update.object_guid, update.chat.count_unseen)
```

| Decorator | Receives | Source (user API) | Source (bot) |
|---|---|---|---|
| `on_message` | `types.Message` / `types.bot.Message` | `message_updates` with `action == "New"` | `NewMessage` |
| `on_edited_message` | `Message` | `action == "Edit"` | `UpdatedMessage` |
| `on_deleted_message` | `Message` / bot `Update` | `action == "Delete"` | `RemovedMessage` |
| `on_chat_update` | `ChatUpdate` | `chat_updates` | – |
| `on_activity` | `ShowActivity` | `show_activities` (typing, recording, uploading) | – |
| `on_notification` | `ShowNotification` | `show_notifications` | – |
| `on_draft_update` | `DraftMessageUpdate` | `draft_message_updates` | – |
| `on_inline_message` | `InlineMessage` | – | webhook inline messages |
| `on_callback_query` | bot `Message` / `InlineMessage` | – | messages with `aux_data.button_id` |
| `on_raw_update` | `Updates` / bot `Update` | every decrypted frame | every update |

`add_handler(handlers.MessageHandler(func, filters), group=0)` and
`remove_handler()` do the same without decorators.

**Groups and propagation.** Handlers live in integer groups, run in ascending
group order; inside a group the first handler whose filter matches runs and the
group is done. Raise `ContinuePropagation` to let the next handler of the same
group run too, `StopPropagation` to stop everything for this update. Handler
exceptions are logged and never stop the dispatcher. Callbacks and filters can
be sync or async.

## Filters

Built-in filters in `rubigram.filters` (they work on user and bot messages):

| Group | Filters |
|---|---|
| chat kind | `private`, `bot`, `group`, `channel`, `service` |
| origin | `me` / `outgoing`, `incoming`, `from_bot`, `forwarded`, `forwarded_no_link`, `scheduled` |
| content | `text`, `caption`, `media`, `photo`, `video`, `gif`, `voice`, `music`, `document`, `sticker`, `location`, `contact`, `poll`, `quiz`, `live`, `rubino`, `event` |
| formatting | `metadata`, `bold`, `italic`, `mono`, `mention` |
| state | `new`, `edited`, `deleted`, `replied` / `reply` |
| group events | `member_added`, `member_joined`, `member_left`, `member_removed`, `message_pinned`, `voice_chat_started`, `voice_chat_finished` |
| bots | `button`, `button_id("id", …)` |
| links | `group_link`, `channel_link` |

Factories: `regex(pattern)` (stores `message.matches`), `command("start")` /
`command(["help", "h"], prefixes="/!")` (stores `message.command = [name, *args]`),
`chat(*guids)`, `user(*guids)`, `create(func, name)`.

Compose with `&`, `|`, `~`. A custom filter:

```python
from rubigram import filters

async def long_text(client, message):
    return len(message.text or "") > 100

only_long = filters.text & filters.create(long_text)
```

## The update objects

A decrypted socket frame is a `types.Updates`:

```
Updates
├── message_updates: [MessageUpdate(message_id, action, message: Message, object_guid, type, …)]
├── chat_updates:    [ChatUpdate(object_guid, action, chat: Chat, updated_parameters, …)]
├── show_activities: [ShowActivity(object_guid, user_guid, activity, type)]
├── show_notifications, draft_message_updates, group_voice_chat_updates
└── user_guid, mode
```

`MessageUpdate` copies `action`, `type` (chat type), `state` and `object_guid`
into its `Message`, so handlers get a self-contained message with
`message.chat_type`, `message.object_guid` and working helpers:
`reply()`, `edit()`, `delete()`, `forward()`, `pin()`/`unpin()`, `react()`,
`seen()`, `download()`.

## Receiving without handlers

```python
async with Client("me") as app:
    frame = await app.receive_update(timeout=30)      # next pushed Updates (opens the socket)
    for update in frame.message_updates:
        print(update.action, update.message.text)

    polled = await app.get_updates(transport="http")  # ChatsUpdates via getChatsUpdates
    per_chat = await app.get_messages_updates("g0…")  # getMessagesUpdates with a stored state
```

The background listener starts only when handlers are registered (or when you
call `idle()`), so `receive_update()` can be driven manually without competing
for frames. Update states (`getChatsUpdates`, per-chat `getMessagesUpdates`,
contacts, folders) are persisted in the session and an `OldState` answer never
moves them backwards.

## Bots

Bots use the same decorators. `bot.run()` polls `getUpdates` with the stored
offset; for webhooks call `await bot.dispatch_webhook_update(body)` from your
HTTP server. See [bot-api.md](bot-api.md).
