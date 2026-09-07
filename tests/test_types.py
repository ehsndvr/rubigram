import asyncio
import json
import pickle
import warnings
from pathlib import Path

import pytest

from rubigram import types
from rubigram.enums import ButtonType
from rubigram.types import (
    Avatar,
    AvatarThumbnail,
    Chat,
    ChatAvatars,
    ChatUpdate,
    GroupMembers,
    Message,
    MessageUpdate,
    PeerObject,
    RawObject,
    RubinoPostsResult,
    SentMessage,
    StickerFile,
    Updates,
    UploadDescriptor,
    User,
    UserInfo,
)
from rubigram.types.bot import BotUpdates, Button, Keypad, KeypadRow, Update

FIXTURES = Path(__file__).parent / "fixtures" / "rubika"


def load_fixture(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def response_data(name: str):
    pairs = load_fixture(name)
    return next(item for item in pairs if "status" in item and "method" not in item)["data"]


class FakeClient:
    def __init__(self):
        self.calls = []

    async def download_file(self, target, **kwargs):
        self.calls.append(("download_file", target, kwargs))
        return b"data"

    async def download_url(self, url, **kwargs):
        self.calls.append(("download_url", url, kwargs))
        return b"data"

    async def send_message(self, **kwargs):
        self.calls.append(("send_message", kwargs))
        return SentMessage(message_update=MessageUpdate(message_id="m2"))

    async def delete_messages(self, object_guid, message_ids, *, delete_type="Global"):
        self.calls.append(("delete_messages", object_guid, message_ids, delete_type))
        return True


def test_user_info_fixture_parses_into_nested_typed_models():
    info = UserInfo._parse(None, response_data("getUserInfo"))
    assert isinstance(info.user, User)
    assert info.user.user_guid.startswith("u0EXAMPLE")
    assert info.user.avatar_thumbnail is None or isinstance(info.user.avatar_thumbnail, AvatarThumbnail)
    assert isinstance(info.chat.avatar_thumbnail, AvatarThumbnail) or info.chat.avatar_thumbnail is None
    assert isinstance(info.chat, Chat)  # cross-module forward reference resolved
    assert isinstance(info.chat.abs_object, PeerObject)
    assert info.chat.abs_object.type == "User"
    assert isinstance(info.user_additional_info, types.UserAdditionalInfo)
    plain = info.to_dict()
    assert plain["user"]["user_guid"] == info.user.user_guid
    assert "u0EXAMPLE" in repr(info)


def test_unknown_fields_are_preserved_as_attributes_and_extra():
    message = Message._parse(None, {"message_id": "1", "type": "Text", "text": "hi", "brand_new_field": {"nested": [1, 2]}})
    assert message.text == "hi"
    assert message.extra["brand_new_field"].nested == [1, 2]
    assert message.brand_new_field.nested == [1, 2]  # type: ignore[attr-defined]
    assert message.to_dict()["brand_new_field"] == {"nested": [1, 2]}
    assert isinstance(message.brand_new_field, RawObject)  # type: ignore[attr-defined]


def test_sticker_message_parses_file_and_downloads_through_bound_client():
    client = FakeClient()
    data = {
        "message_id": "5",
        "type": "Sticker",
        "object_guid": "u0EXAMPLE00000000000000000000001",
        "sticker": {"sticker_id": "s1", "emoji_character": "😀", "w_h_ratio": "1.0", "file": {"file_id": "f1", "dc_id": "3", "access_hash_rec": "ACCESS", "mime": "png", "file_name": "s.png"}},
    }
    message = Message._parse(client, data)
    assert isinstance(message.sticker.file, StickerFile)
    assert message.sticker.file.file_id == "f1"
    assert message.sticker._client is client and message.sticker.file._client is client
    assert asyncio.run(message.sticker.download(in_memory=True)) == b"data"
    assert asyncio.run(message.download(in_memory=True)) == b"data"
    assert [call[0] for call in client.calls] == ["download_file", "download_file"]
    assert client.calls[0][1] is message.sticker.file


def test_socket_update_fixture_copies_envelope_fields_onto_messages():
    frame = load_fixture("socket_update")
    updates = Updates._parse(None, frame)
    assert updates.message_updates and updates.chat_updates
    first = updates.message_updates[0]
    assert isinstance(first, MessageUpdate)
    assert first.message.action == first.action == "New"
    assert first.message.chat_type == first.type
    assert first.message.object_guid == first.object_guid
    assert first.message.message_id == first.message_id
    assert updates.messages[0] is first.message
    chat_update = updates.chat_updates[0]
    assert isinstance(chat_update, ChatUpdate)
    assert chat_update.chat.last_message.object_guid == chat_update.object_guid
    assert not updates.is_empty and Updates._parse(None, {}).is_empty


def test_avatars_are_list_like_and_download_with_generated_names():
    client = FakeClient()
    avatars = ChatAvatars._parse(client, response_data("getAvatars"))
    assert len(avatars) >= 1 and isinstance(avatars[0], Avatar)
    assert list(avatars) == avatars.avatars
    result = asyncio.run(avatars[-1].download(in_memory=True, file_name="avatar.jpg"))
    assert result == b"data"
    assert client.calls[-1][1] is avatars[-1].main
    assert client.calls[-1][2]["file_name"] == "avatar.jpg"
    asyncio.run(avatars.download(in_memory=True, use_thumbnail=True))
    names = [call[2]["file_name"] for call in client.calls[1:]]
    assert all(name.endswith("_thumbnail.jpg") for name in names)
    with pytest.raises(RuntimeError):
        asyncio.run(Avatar(avatar_id="x").download())


def test_message_reply_delete_use_bound_client():
    client = FakeClient()
    message = Message._parse(client, {"message_id": "m1", "object_guid": "u0EXAMPLE00000000000000000000002", "type": "Text", "text": "hi"})
    sent = asyncio.run(message.reply("pong"))
    kwargs = client.calls[0][1]
    assert kwargs["object_guid"] == message.object_guid
    assert kwargs["reply_to_message_id"] == "m1" and kwargs["text"] == "pong" and kwargs["rnd"]
    assert sent.message_id == "m2"
    asyncio.run(message.delete())
    assert client.calls[1] == ("delete_messages", message.object_guid, ["m1"], "Global")
    with pytest.raises(RuntimeError):
        asyncio.run(Message(message_id="1").reply("x"))


def test_group_members_fixture_and_iteration():
    members = GroupMembers._parse(None, response_data("getGroupAllMembers"))
    assert len(members) == len(members.in_chat_members)
    assert all(isinstance(member, types.GroupMember) for member in members)
    assert "EXAMPLE" in members.in_chat_members[0].member_guid


def test_rubino_post_result_names_files_from_post_id():
    client = FakeClient()
    result = RubinoPostsResult._parse(
        client,
        {
            "posts": [{"id": "p1", "profile_id": "pp1", "file_type": "Video", "full_file_url": "https://rubino2.iranlms.ir/video/file-1", "full_thumbnail_url": "https://rubino2.iranlms.ir/picture/thumb-1"}],
            "liked_posts": [],
            "bookmarked_posts": [],
        },
    )
    assert result.post is result.posts[0]
    assert result.post.file.file_name == "p1.mp4"
    assert result.post.thumbnail.file_name == "p1_thumbnail.jpg"
    assert result.post.snapshot is None
    asyncio.run(result.post.download(in_memory=True))
    assert client.calls[0][1] == "https://rubino2.iranlms.ir/video/file-1"
    assert client.calls[0][2]["file_name"] == "p1.mp4"


def test_raw_object_keeps_keys_and_equality_pickle_repr():
    raw = RawObject._parse(None, {"a": 1, "nested": {"b": [1, {"c": 2}]}, "not-an-identifier": 3})
    assert raw.a == 1 and raw.nested.b[1].c == 2
    assert raw.get("not-an-identifier") == 3 and "not-an-identifier" in raw
    assert raw.to_dict() == {"a": 1, "nested": {"b": [1, {"c": 2}]}, "not-an-identifier": 3}
    with pytest.raises(AttributeError):
        raw.missing
    descriptor = UploadDescriptor(id="1", dc_id="2", access_hash_send="s")
    assert descriptor == UploadDescriptor(id="1", dc_id="2", access_hash_send="s")
    assert descriptor != UploadDescriptor(id="9")
    assert pickle.loads(pickle.dumps(descriptor)) == descriptor
    assert "UploadDescriptor(id='1'" in repr(descriptor)
    assert json.loads(str(descriptor))["_"] == "UploadDescriptor"


def test_bot_keypad_serialization_and_updates_bind_chat_id():
    keypad = Keypad(rows=[KeypadRow(buttons=[Button(id="1", type="Simple", button_text="Open")])])
    assert keypad.to_dict() == {"rows": [{"buttons": [{"id": "1", "type": "Simple", "button_text": "Open"}]}]}
    built = Keypad.build([Button.simple("a", "A")], resize_keyboard=True)
    assert built.to_dict()["rows"][0]["buttons"][0]["type"] == "Simple"
    assert built.rows[0].buttons[0].type is ButtonType.SIMPLE
    updates = BotUpdates._parse(
        None,
        {"updates": [{"type": "NewMessage", "chat_id": "c0", "new_message": {"message_id": "m1", "text": "/start", "sender_type": "User", "sender_id": "u1"}}], "next_offset_id": "2"},
    )
    update = updates.updates[0]
    assert isinstance(update, Update) and update.new_message.chat_id == "c0"
    assert update.new_message.type == "Text" and update.new_message.chat_type == "User" and update.new_message.is_mine is False
    assert update.message is update.new_message
    assert types.bot.SentMessage._parse(None, {"new_message_id": 7}).message_id == "7"
    assert types.bot.SentMessage._parse(None, "8").message_id == "8"


def test_deprecated_import_paths_still_work():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import importlib

        results = importlib.import_module("rubigram.types.results")
        importlib.reload(results)
        bot_types = importlib.import_module("rubigram.bot.types")
        importlib.reload(bot_types)
    assert results.Message is Message
    assert bot_types.Keypad is Keypad
    assert sum(issubclass(w.category, DeprecationWarning) for w in caught) >= 2
