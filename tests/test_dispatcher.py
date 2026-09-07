"""Filters, handlers and the dispatcher, driven by recorded socket frames."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rubigram import Client, ContinuePropagation, StopPropagation, filters, handlers, types
from rubigram.handlers import Dispatcher, MessageHandler
from rubigram.types.bot import InlineMessage, Update as BotUpdate

from .fake_rubika import install, run, seed_session

SOCKET_FRAME = json.loads((Path(__file__).parent / "fixtures" / "rubika" / "socket_update.json").read_text(encoding="utf-8"))


def message(**kwargs) -> types.Message:
    return types.Message(client=None, **kwargs)


# ---------------------------------------------------------------------------
# filters
# ---------------------------------------------------------------------------


def test_builtin_filters_read_user_and_bot_messages():
    async def scenario():
        text = message(message_id="1", type="Text", text="hello", chat_type="User", is_mine=False)
        assert await filters.text(None, text) and await filters.private(None, text) and await filters.incoming(None, text)
        assert not await filters.group(None, text) and not await filters.me(None, text)
        photo = message(message_id="2", type="FileInline", file_inline=types.FileInline(client=None, type="Image"), chat_type="Group")
        assert await filters.photo(None, photo) and await filters.media(None, photo) and await filters.group(None, photo)
        assert not await filters.video(None, photo)
        edited = message(message_id="3", action="Edit", text="x")
        assert await filters.edited(None, edited) and not await filters.new(None, edited)
        bot_message = types.bot.Message(client=None, message_id="4", text="/start now", chat_id="b0chat", sender_type="User")
        assert await filters.text(None, bot_message)
        assert await filters.command("start")(None, bot_message)
        assert not await filters.command("stop")(None, bot_message)
        assert await filters.command(["help", "start"], prefixes=["/", "!"])(None, types.bot.Message(client=None, message_id="5", text="!Start"))

    run(scenario())


def test_filter_composition_regex_chat_and_custom_async():
    async def scenario():
        msg = message(message_id="1", type="Text", text="order 42", object_guid="g1", author_object_guid="u1", chat_type="Group")
        combined = filters.text & filters.group & ~filters.private
        assert await combined(None, msg)
        assert await (filters.private | filters.group)(None, msg)
        matched = filters.regex(r"order (\d+)")
        assert await matched(None, msg) and msg.matches[0].group(1) == "42"
        assert await filters.chat("g1")(None, msg) and not await filters.chat("g2")(None, msg)
        assert await filters.user("u1")(None, msg)

        async def slow(client, update):
            return update.text.startswith("order")

        assert await filters.create(slow)(None, msg)
        assert repr(filters.text & filters.group).startswith("rubigram.filters.")
        with pytest.raises(TypeError):
            filters.create(slow).check_sync(None, msg)

    run(scenario())


# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------


def test_dispatcher_groups_and_propagation_control():
    async def scenario():
        seen = []
        dispatcher = Dispatcher(client=None)

        async def first(client, update):
            seen.append("first")
            raise ContinuePropagation

        async def second(client, update):
            seen.append("second")

        async def third(client, update):
            seen.append("third")

        def other_group(client, update):
            seen.append("group-1")
            raise StopPropagation

        def never(client, update):
            seen.append("never")

        dispatcher.add_handler(MessageHandler(first), 0)
        dispatcher.add_handler(MessageHandler(second), 0)
        dispatcher.add_handler(MessageHandler(third), 0)  # same group, after a match → skipped
        dispatcher.add_handler(MessageHandler(other_group), 1)
        dispatcher.add_handler(MessageHandler(never), 2)
        await dispatcher.dispatch("message", message(message_id="1"))
        assert seen == ["first", "second", "group-1"]
        assert dispatcher.remove_handler(dispatcher.handlers("message")[0]) and len(dispatcher.handlers()) == 4

        failing = MessageHandler(lambda c, u: 1 / 0, filters.all)
        dispatcher.groups.clear()
        dispatcher.add_handler(failing)
        await dispatcher.dispatch("message", message(message_id="2"))  # exceptions are logged, not raised

    run(scenario())


def test_socket_frame_is_routed_to_typed_handlers(monkeypatch):
    async def scenario():
        rubika, _ = install(monkeypatch)
        client = Client("test", in_memory=True, interactive=False, enable_socket=False, transport="http")
        received = {"message": [], "chat": [], "raw": [], "edited": []}

        @client.on_message(filters.text)
        async def on_text(app, msg):
            assert app is client and isinstance(msg, types.Message)
            received["message"].append(msg)

        @client.on_edited_message()
        async def on_edit(app, msg):
            received["edited"].append(msg)

        @client.on_chat_update()
        async def on_chat(app, update):
            received["chat"].append(update)

        @client.on_raw_update()
        async def on_raw(app, update):
            received["raw"].append(update)

        updates = types.Updates._parse(client, SOCKET_FRAME)
        await client.dispatch_update(updates)
        assert len(received["raw"]) == 1 and isinstance(received["raw"][0], types.Updates)
        assert received["message"] and received["message"][0].text == "sample text"
        assert received["message"][0].object_guid == "u0EXAMPLE00000000000000000000001"
        assert received["message"][0]._client is client  # bound helpers work
        assert received["chat"] and received["chat"][0].chat.last_message.message_id == "1556351220500832"
        assert received["edited"] == []
        assert client.dispatcher.has_handlers("message")
        # the user-facing registration API exposes the handler objects too
        assert any(isinstance(h, handlers.MessageHandler) for h in client.dispatcher.handlers())

    run(scenario())


def test_bot_updates_and_inline_messages_are_routed(monkeypatch):
    async def scenario():
        install(monkeypatch)
        client = Client("bot", token="1:fake", in_memory=True)
        seen = {"message": [], "callback": [], "inline": [], "deleted": []}

        @client.on_message(filters.command("start"))
        async def start(app, msg):
            seen["message"].append(msg.chat_id)

        @client.on_callback_query(filters.button_id("btn-1"))
        async def pressed(app, msg):
            seen["callback"].append(msg.aux_data.button_id)

        @client.on_inline_message()
        async def inline(app, msg):
            seen["inline"].append(msg.message_id)

        @client.on_deleted_message()
        async def removed(app, update):
            seen["deleted"].append(update.removed_message_id)

        update = BotUpdate._parse(client, {"type": "NewMessage", "chat_id": "b0chat", "new_message": {"message_id": "1", "text": "/start", "sender_type": "User"}})
        await client.dispatch_update(update)
        button = BotUpdate._parse(client, {"type": "NewMessage", "chat_id": "b0chat", "new_message": {"message_id": "2", "text": "menu", "aux_data": {"button_id": "btn-1"}}})
        await client.dispatch_update(button)
        await client.dispatch_update(BotUpdate._parse(client, {"type": "RemovedMessage", "chat_id": "b0chat", "removed_message_id": "9"}))
        await client.dispatch_update(InlineMessage._parse(client, {"message_id": "3", "chat_id": "b0chat", "aux_data": {"button_id": "btn-1"}}))
        assert seen == {"message": ["b0chat"], "callback": ["btn-1", "btn-1"], "inline": ["3"], "deleted": ["9"]}

    run(scenario())


def test_http_polling_loop_turns_new_last_messages_into_message_events(monkeypatch):
    async def scenario():
        rubika, _ = install(monkeypatch)
        client = Client("test", in_memory=True, interactive=False, enable_socket=False, transport="http", poll_interval=0.01)
        await seed_session(client)
        got = []

        @client.on_message()
        async def any_message(app, msg):
            got.append((msg.object_guid, msg.message_id, msg.text))
            await app.stop()

        rubika.responses["getChatsUpdates"] = [
            {"chats": [{"object_guid": "g1", "type": "Group", "last_message": {"message_id": "1", "text": "old"}}], "new_state": 1},
            {"chats": [{"object_guid": "g1", "type": "Group", "last_message": {"message_id": "2", "text": "new"}}], "new_state": 2},
            {"chats": [], "new_state": 3},
        ]
        await client.start()
        assert client._listener_task is not None
        await client.idle()
        assert got == [("g1", "2", "new")]
        assert not client.is_connected

    run(scenario())
