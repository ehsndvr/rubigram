import asyncio

from rubigram import Client, filters
from rubigram.bot.types import Button, BotUpdates, Keypad, KeypadRow


def test_client_unwraps_bot_ok_result():
    client = Client("bot", token="token", in_memory=True)
    result = client._unwrap_bot_response({"ok": True, "result": {"message_id": "1"}})
    assert result == {"message_id": "1"}


def test_client_parses_bot_updates_and_binds_message_helpers():
    client = Client("bot", token="token", in_memory=True)
    updates = BotUpdates._parse(
        client,
        {
            "updates": [
                {
                    "type": "NewMessage",
                    "chat_id": "c0",
                    "new_message": {
                        "message_id": "m1",
                        "text": "hello",
                        "sender_type": "User",
                        "sender_id": "u1",
                    },
                }
            ],
            "next_offset_id": "2",
        },
    )

    assert updates.next_offset_id == "2"
    assert updates.updates[0].new_message.chat_id == "c0"
    assert updates.updates[0].new_message._client is client


def test_client_get_me_unwraps_nested_bot_payload():
    async def scenario():
        client = Client("bot", token="token", in_memory=True)
        await client.start()

        class StubBotTransport:
            async def call_method(self, method, payload=None):
                assert method == "getMe"
                return {"ok": True, "result": {"bot": {"bot_id": "b0", "bot_title": "Test Bot", "username": "testbot"}}}

            async def close(self):
                return None

        client._bot_transport = StubBotTransport()  # type: ignore[assignment]
        me = await client.get_me()

        assert me.bot_id == "b0"
        assert me.bot_title == "Test Bot"
        assert me.username == "testbot"

        await client.stop()

    asyncio.run(scenario())


def test_bot_keypad_serialization_accepts_typed_buttons():
    keypad = Keypad(rows=[KeypadRow(buttons=[Button(id="1", type="Simple", button_text="Open")])])
    assert keypad.to_dict() == {
        "rows": [
            {
                "buttons": [
                    {
                        "id": "1",
                        "type": "Simple",
                        "button_text": "Open",
                    }
                ]
            }
        ]
    }


def test_client_persists_token_in_session_string():
    async def scenario():
        client = Client("bot", token="token-123", in_memory=True)
        await client.start()
        session_string = await client.export_session_string()
        await client.stop()

        restored = Client("bot-restored", session_string=session_string)
        await restored.start()

        assert restored.is_bot is True
        assert restored.token == "token-123"

        await restored.stop()

    asyncio.run(scenario())


def test_client_send_message_uses_bot_api_shape():
    async def scenario():
        client = Client("bot", token="token-123", in_memory=True)
        await client.start()

        class StubBotTransport:
            async def call_method(self, method, payload=None):
                assert method == "sendMessage"
                assert payload == {"chat_id": "c0", "text": "hello", "disable_notification": False}
                return {"ok": True, "result": {"message_id": "m1"}}

            async def close(self):
                return None

        client._bot_transport = StubBotTransport()  # type: ignore[assignment]
        result = await client.send_message("c0", text="hello")

        assert result.message_id == "m1"
        await client.stop()

    asyncio.run(scenario())


def test_client_send_message_accepts_positional_text_in_bot_mode():
    async def scenario():
        client = Client("bot", token="token-123", in_memory=True)
        await client.start()

        class StubBotTransport:
            async def call_method(self, method, payload=None):
                assert method == "sendMessage"
                assert payload == {"chat_id": "c0", "text": "hello", "disable_notification": False}
                return {"ok": True, "result": {"message_id": "m1"}}

            async def close(self):
                return None

        client._bot_transport = StubBotTransport()  # type: ignore[assignment]
        result = await client.send_message("c0", "hello")

        assert result.message_id == "m1"
        await client.stop()

    asyncio.run(scenario())


def test_bot_polling_dispatches_message_handlers():
    async def scenario():
        client = Client("bot", token="token", in_memory=True)
        seen = []

        @client.on_message()
        async def handle_message(app, message):
            seen.append((app.token, message.text))

        async def fake_get_updates(offset_id=None, limit=None):
            client._bot_polling_stop.set()
            return BotUpdates._parse(
                client,
                {
                    "updates": [
                        {
                            "type": "NewMessage",
                            "chat_id": "c0",
                            "new_message": {"message_id": "m1", "text": "ping"},
                        }
                    ],
                    "next_offset_id": "10",
                },
            )

        client.get_updates = fake_get_updates  # type: ignore[method-assign]
        await client.start_polling(limit=10, idle_sleep=0)
        await asyncio.wait_for(client._bot_polling_task, timeout=1)

        assert seen == [("token", "ping")]

    asyncio.run(scenario())


def test_bot_polling_applies_filters():
    async def scenario():
        client = Client("bot", token="token", in_memory=True)
        seen = []

        @client.on_message(filters.text & filters.private & ~filters.me)
        async def handle_message(app, message):
            seen.append(message.text)

        async def fake_get_updates(offset_id=None, limit=None):
            client._bot_polling_stop.set()
            return BotUpdates._parse(
                client,
                {
                    "updates": [
                        {
                            "type": "NewMessage",
                            "chat_id": "c0",
                            "new_message": {
                                "message_id": "m1",
                                "text": "hello",
                                "sender_type": "User",
                            },
                        }
                    ],
                    "next_offset_id": "10",
                },
            )

        client.get_updates = fake_get_updates  # type: ignore[method-assign]
        await client.start_polling(limit=10, idle_sleep=0)
        await asyncio.wait_for(client._bot_polling_task, timeout=1)

        assert seen == ["hello"]

    asyncio.run(scenario())


def test_bot_command_filter_parses_command_and_args():
    async def scenario():
        client = Client("bot", token="token", in_memory=True)
        seen = []

        @client.on_message(filters.command("start"))
        async def handle_message(app, message):
            seen.append(message.command)

        async def fake_get_updates(offset_id=None, limit=None):
            client._bot_polling_stop.set()
            return BotUpdates._parse(
                client,
                {
                    "updates": [
                        {
                            "type": "NewMessage",
                            "chat_id": "c0",
                            "new_message": {
                                "message_id": "m1",
                                "text": "/start hello world",
                                "sender_type": "User",
                            },
                        }
                    ],
                    "next_offset_id": "10",
                },
            )

        client.get_updates = fake_get_updates  # type: ignore[method-assign]
        await client.start_polling(limit=10, idle_sleep=0)
        await asyncio.wait_for(client._bot_polling_task, timeout=1)

        assert seen == [["start", "hello", "world"]]

    asyncio.run(scenario())


def test_bot_edit_message_text_alias_and_upload_file_alias():
    async def scenario():
        client = Client("bot", token="token", in_memory=True)
        await client.start()
        calls = []

        class StubBotTransport:
            async def call_method(self, method, payload=None):
                calls.append((method, payload))
                if method == "editMessageText":
                    return {"ok": True, "result": {"message_id": "m2"}}
                raise AssertionError(method)

            async def upload_file(self, upload_url, path):
                assert upload_url == "https://upload.example"
                assert path == "sample.bin"
                return {"ok": True, "result": {"file_id": "f1"}}

            async def close(self):
                return None

        client._bot_transport = StubBotTransport()  # type: ignore[assignment]
        edited = await client.edit_message_text("c0", "m1", "updated")
        uploaded = await client.upload_file(path="sample.bin", upload_url="https://upload.example")

        assert edited.message_id == "m2"
        assert uploaded == "f1"
        assert calls == [("editMessageText", {"chat_id": "c0", "message_id": "m1", "text": "updated"})]

        await client.stop()

    asyncio.run(scenario())
