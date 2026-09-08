"""``Client(token=...)``: the Bot API through the same client class."""
# pyright: reportOptionalMemberAccess=false
# (tests assert on parsed payloads; a missing field is a test failure)

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from rubigram import Client, errors, types
from rubigram.enums import ButtonType, ChatKeypadType
from rubigram.types.bot import Button, Keypad, KeypadRow

from .fake_rubika import FakeBotTransport, install, run


async def started(monkeypatch, **kwargs):
    install(monkeypatch)
    client = Client("bot", token="1:fake", in_memory=True, **kwargs)
    await client.start()
    return client, cast(FakeBotTransport, client._bot)


def test_bot_start_persists_token_and_refuses_user_rpcs(monkeypatch):
    async def scenario():
        client, bot = await started(monkeypatch)
        assert client.is_bot and client.is_connected and bot.token == "1:fake"
        assert await client.storage.bot_token() == "1:fake"
        with pytest.raises(errors.TransportError):
            await client.invoke_raw("getChats")
        with pytest.raises(errors.RubigramError):
            await client.get_chats()
        await client.stop()
        assert bot.closed and not client.is_connected

    run(scenario())


def test_send_message_serializes_keypads_and_parses_sent_message(monkeypatch):
    async def scenario():
        client, bot = await started(monkeypatch)
        bot.responses["sendMessage"] = {"message_id": "77"}
        keypad = Keypad(
            client=None,
            rows=[KeypadRow(client=None, buttons=[Button(client=None, id="btn-1", type=ButtonType.SIMPLE, button_text="Go")])],
            resize_keyboard=True,
        )
        sent = await client.send_message(
            "b0chat",
            "hello",
            inline_keypad=keypad,
            chat_keypad=keypad,
            chat_keypad_type=ChatKeypadType.NEW,
            disable_notification=True,
            reply_to_message_id="5",
        )
        assert isinstance(sent, types.bot.SentMessage) and sent.message_id == "77"
        payload = bot.payload("sendMessage")
        assert payload["chat_id"] == "b0chat" and payload["text"] == "hello" and payload["disable_notification"] is True
        assert payload["chat_keypad_type"] == "New" and payload["reply_to_message_id"] == "5"
        assert payload["inline_keypad"] == {
            "rows": [{"buttons": [{"id": "btn-1", "type": "Simple", "button_text": "Go"}]}],
            "resize_keyboard": True,
        }
        with pytest.raises(ValueError):
            await client.send_message("b0chat")
        await client.stop()

    run(scenario())


def test_bot_helpers_map_to_bot_api_methods(monkeypatch):
    async def scenario():
        client, bot = await started(monkeypatch)
        bot.responses.update(
            {
                "getMe": {"bot": {"bot_id": "b1", "username": "sample_bot"}},
                "getChat": {"chat": {"chat_id": "b0chat", "chat_type": "User"}},
                "forwardMessage": {"message_id": "8"},
                "editMessageText": {"message_id": "1"},
                "sendPoll": {"message_id": "9"},
                "sendLocation": {"message_id": "10"},
                "sendContact": {"message_id": "11"},
            }
        )
        me = await client.get_me()
        assert isinstance(me, types.bot.Bot) and me.username == "sample_bot"
        chat = await client.get_chat("b0chat")
        assert isinstance(chat, types.bot.Chat) and chat.chat_id == "b0chat"
        assert (await client.forward_message("b0a", "1", "b0b")).message_id == "8"
        assert bot.payload("forwardMessage") == {
            "from_chat_id": "b0a",
            "message_id": "1",
            "to_chat_id": "b0b",
            "disable_notification": False,
        }
        await client.edit_message_text("b0chat", "1", "edited")
        await client.edit_message("b0chat", "1", "edited again")
        assert [p["text"] for m, p in bot.calls if m == "editMessageText"] == ["edited", "edited again"]
        assert await client.delete_message("b0chat", "1") is True
        assert bot.payload("deleteMessage") == {"chat_id": "b0chat", "message_id": "1"}
        await client.send_poll("b0chat", "Q?", ["a", "b"])
        assert bot.payload("sendPoll") == {"chat_id": "b0chat", "question": "Q?", "options": ["a", "b"]}
        await client.send_location("b0chat", 35.7, 51.4)
        assert bot.payload("sendLocation")["latitude"] == "35.7"
        await client.send_contact("b0chat", "A", "B", "+1")
        assert bot.payload("sendContact")["phone_number"] == "+1"
        assert await client.set_commands([types.bot.BotCommand(client=None, command="start", description="Start")]) is True
        assert bot.payload("setCommands") == {"bot_commands": [{"command": "start", "description": "Start"}]}
        assert await client.update_bot_endpoints("https://example.test/hook", "ReceiveUpdate") is True
        assert await client.edit_chat_keypad("b0chat", chat_keypad_type="Remove") is True
        assert bot.payload("editChatKeypad") == {"chat_id": "b0chat", "chat_keypad_type": "Remove"}
        assert await client.ban_chat_member("b0chat", "u1") is True and await client.unban_chat_member("b0chat", "u1") is True
        await client.stop()

    run(scenario())


def test_bot_updates_persist_offset_and_files_round_trip(monkeypatch, tmp_path):
    async def scenario():
        client, bot = await started(monkeypatch)
        bot.responses["getUpdates"] = [
            {
                "updates": [{"type": "NewMessage", "chat_id": "b0chat", "new_message": {"message_id": "1", "text": "hi"}}],
                "next_offset_id": "off-1",
            },
            {"updates": [], "next_offset_id": "off-2"},
        ]
        updates = await client.get_updates()
        assert isinstance(updates, types.bot.BotUpdates) and len(updates) == 1 and updates.updates[0].new_message.chat_id == "b0chat"
        assert await client.storage.bot_offset_id() == "off-1"
        await client.get_bot_updates(limit=5)
        assert bot.calls[-1] == ("getUpdates", {"offset_id": "off-1", "limit": 5})

        bot.responses["requestSendFile"] = {"upload_url": "https://upload.example/x"}
        bot.responses["sendFile"] = {"message_id": "12"}
        photo = tmp_path / "pic.jpg"
        photo.write_bytes(b"data")
        sent = await client.send_photo("b0chat", photo, text="cap")
        assert sent.message_id == "12" and bot.uploads == [("https://upload.example/x", str(photo))]
        assert bot.payload("requestSendFile") == {"type": "Image"}
        assert bot.payload("sendFile") == {"chat_id": "b0chat", "file_id": "file-42", "text": "cap", "disable_notification": False}

        bot.responses["getFile"] = {"file": {"file_id": "file-42", "file_name": "pic.jpg", "download_url": "https://dl.example/pic.jpg"}}
        target = await client.download_file("file-42", tmp_path)
        assert isinstance(target, Path) and target == tmp_path / "pic.jpg" and target.read_bytes() == b"bot-bytes"
        assert (
            await client.download_bot_file(types.bot.File(client=None, file_id="f", download_url="https://dl.example/f"), in_memory=True)
            == b"bot-bytes"
        )
        await client.stop()

    run(scenario())


def test_webhook_payloads_are_parsed_and_dispatched(monkeypatch):
    async def scenario():
        client, bot = await started(monkeypatch)
        seen = []

        @client.on_message()
        async def any_message(app, msg):
            seen.append(("message", msg.message_id))

        @client.on_inline_message()
        async def inline(app, msg):
            seen.append(("inline", msg.message_id))

        parsed = await client.parse_webhook_update(
            {"update": {"type": "NewMessage", "chat_id": "b0chat", "new_message": {"message_id": "1", "text": "x"}}}
        )
        assert parsed.update.new_message.chat_id == "b0chat" and seen == []
        await client.dispatch_webhook_update({"inline_message": {"message_id": "2", "chat_id": "b0chat", "aux_data": {"button_id": "b"}}})
        await client.dispatch_webhook_update(
            {"update": {"type": "NewMessage", "chat_id": "b0chat", "new_message": {"message_id": "3", "text": "y"}}}
        )
        assert seen == [("inline", "2"), ("message", "3")]
        await client.stop()

    run(scenario())


def test_bot_send_message_hint_for_user_guids(monkeypatch):
    async def scenario():
        client, bot = await started(monkeypatch)
        bot.responses["sendMessage"] = errors.InvalidInput("ERROR_GENERIC", "INVALID_INPUT", {}, method="sendMessage")
        with pytest.raises(errors.InvalidInput) as info:
            await client.send_message("u0EXAMPLE00000000000000000000001", "hi")
        assert "chat_id" in str(info.value)
        await client.stop()

    run(scenario())
