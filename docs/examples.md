# Examples

All examples live in [`examples/`](../examples). They read credentials from
environment variables and store sessions next to the script; none contains a
phone number, code or token.

| File | What it shows |
|---|---|
| [`user_session.py`](../examples/user_session.py) | first login with a `code_callback`, `get_me()`, listing chats, replying to private messages |
| [`echo_bot.py`](../examples/echo_bot.py) | a Bot API bot (`RUBIGRAM_BOT_TOKEN`) with `filters.command` and `message.reply()` |
| [`get_rubino_post.py`](../examples/get_rubino_post.py) | fetching a Rubino post by id or from a shared message and downloading it |
| [`rubino_downloader_bot.py`](../examples/rubino_downloader_bot.py) | a user-session bot that answers every shared Rubino post with the media file |
| [`ai_assistant.py`](../examples/ai_assistant.py) | answering questions with an OpenAI-compatible API, grounded in this documentation |

## Snippets

Send media with a caption and progress:

```python
async def progress(current, total, label):
    print(f"{label}: {current}/{total}")

await app.send_video("g0…", "clip.mp4", text="caption", duration_ms=12000, width=1280, height=720,
                     progress=progress, progress_args=("upload",))
```

Walk a chat history:

```python
async for message in app.iter_messages("c0…", limit=200):
    print(message.message_id, message.text)
```

Manage a group:

```python
info = await app.get_group_info("g0…")
await app.set_group_admin("g0…", "u0…", ["PinMessages", "DeleteGlobalAllMessages"])
link = await app.create_join_link("g0…", "friends", usage_limit=10)
await app.edit_group_info("g0…", slow_mode=30, event_messages=False)
```

React, pin, forward:

```python
reactions = await app.get_available_reactions()
await message.react(reactions.reactions[0].reaction_id)
await message.pin()
await message.forward("u0…")
```

Poll updates without a socket:

```python
app = Client("me", transport="http")
async with app:
    updates = await app.get_chats_updates()
    for chat in updates.chats:
        print(chat.object_guid, chat.last_message and chat.last_message.text)
```

Call a method that has no wrapper:

```python
result = await app.invoke_raw("getChatAds", {"state": 0})
print(result.to_dict())
```

## Live tests

`tests/integration/` contains read-only checks against the real servers. They
are skipped unless `RUBIGRAM_INTEGRATION=1`; a user test needs a session file
created by `examples/user_session.py` (`RUBIGRAM_SESSION=<name>`), the bot
test needs `RUBIGRAM_BOT_TOKEN`.
