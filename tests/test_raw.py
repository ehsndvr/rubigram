import json
from pathlib import Path

import pytest

from rubigram import raw
from rubigram.enums import BlockAction, DcType, MessageEntityType
from rubigram.raw.base import RawMethod, serialize_value
from rubigram.raw.functions import (
    build_data_object,
    build_file_inline,
    build_message_metadata,
    build_plain_payload,
    build_service_client_info,
    build_settings_input,
    build_updated_parameters,
    build_web_client_info,
    guess_upload_mime,
    parse_html,
    parse_markdown,
)
from rubigram.raw.methods import (
    METHODS,
    BlockUser,
    DeleteMessage,
    DeleteMessages,
    GetBaseInfo,
    GetChat,
    GetChatsByID,
    GetHistory,
    GetMessages,
    GetProfilePosts,
    GetUserInfo,
    SendChatActivity,
    SendCode,
    SendMessage,
    SetBlockUser,
    SetGroupAdmin,
    SignIn,
    UnblockUser,
    UnregisterDevice,
    UploadAvatar,
    UploadNewGroupAvatar,
    method_for,
)
from rubigram.types import MessageEntity, RawObject, UserInfo

WEB_METHODS = Path(__file__).parent.parent / "docs" / "redesign" / "web-methods.json"


def test_every_web_client_method_has_a_raw_class():
    names = {row["method"] for row in json.loads(WEB_METHODS.read_text(encoding="utf-8"))["methods"]}
    transport_level = {"handShake", "getDCs"}
    missing = sorted(names - transport_level - set(METHODS))
    assert not missing, missing
    assert len(METHODS) >= len(names) - len(transport_level)
    assert method_for("getUserInfo") is GetUserInfo
    with pytest.raises(KeyError):
        method_for("nope")


def test_generic_serialization_drops_none_and_converts_enums_and_models():
    method = SetBlockUser(user_guid="u1", action=BlockAction.UNBLOCK)
    assert method.to_input() == {"user_guid": "u1", "action": "Unblock"}
    assert SendMessage(object_guid="g", rnd="1", text="hi", parse_mode="markdown").to_input() == {"object_guid": "g", "rnd": "1", "text": "hi"}
    assert serialize_value({"a": None, "b": [MessageEntityType.BOLD]}) == {"b": ["Bold"]}
    assert GetMessages(object_guid="g", max_id="5").to_input() == {"object_guid": "g", "max_id": "5", "sort": "FromMax", "limit": 20}
    assert SetGroupAdmin(group_guid="g", member_guid="u", action="UnsetAdmin").to_input() == {"group_guid": "g", "member_guid": "u", "action": "UnsetAdmin"}
    assert "SetGroupAdmin(" in repr(SetGroupAdmin(group_guid="g", member_guid="u"))


def test_deprecated_aliases_map_to_the_real_rpcs():
    assert BlockUser("u1").name == "setBlockUser" and BlockUser("u1").to_input() == {"user_guid": "u1", "action": "Block"}
    assert UnblockUser(object_guid="u1").to_input()["action"] == "Unblock"
    assert isinstance(BlockUser("u1"), SetBlockUser)
    delete = DeleteMessage("g1", "m1")
    assert isinstance(delete, DeleteMessages) and delete.to_input() == {"object_guid": "g1", "message_ids": ["m1"], "type": "Global"}
    chat = GetChat("g1")
    assert isinstance(chat, GetChatsByID) and chat.name == "getChatsByID" and chat.to_input() == {"object_guids": ["g1"]}
    assert GetHistory(object_guid="g1").name == "getMessages"
    avatar = UploadNewGroupAvatar("g1", "f1", "5", "rec")
    assert isinstance(avatar, UploadAvatar) and avatar.to_input() == {"object_guid": "g1", "thumbnail_file_id": "f1", "main_file_id": "f1"}


def test_auth_modes_api_versions_and_dc_types():
    assert SendCode.auth_mode == "tmp" and SendCode.api_version == "6"
    assert SignIn.unwrap_auth_on_success is True
    assert GetUserInfo.auth_mode == "auth" and GetUserInfo.dc_type is DcType.API
    assert GetProfilePosts.auth_mode == "none" and GetProfilePosts.dc_type is DcType.RUBINO and GetProfilePosts.api_version == "0"
    assert GetBaseInfo.service_url.startswith("https://servicesbase")
    assert UnregisterDevice.auth_mode == "none" and UnregisterDevice.api_version == "4"
    assert SendChatActivity.retries == 0
    with pytest.raises(TypeError):
        RawMethod()  # type: ignore[abstract]


def test_parse_response_uses_result_model_or_raw_object():
    typed = GetUserInfo(user_guid="u").parse_response(None, {"user": {"user_guid": "u", "first_name": "A"}})
    assert isinstance(typed, UserInfo) and typed.user.first_name == "A"
    untyped = raw.methods.GetBotInfo(bot_guid="b").parse_response(None, {"bot": {"bot_guid": "b"}})
    assert isinstance(untyped, RawObject) and untyped.bot.bot_guid == "b"
    assert isinstance(raw.methods.Logout().parse_response(None, None), RawObject)


def test_message_metadata_from_markdown_html_and_entities():
    text, metadata = build_message_metadata("hello **bold** and `mono`", parse_mode="markdown")
    assert text == "hello bold and mono"
    assert metadata == {"meta_data_parts": [{"type": "Bold", "from_index": 6, "length": 4}, {"type": "Mono", "from_index": 15, "length": 4}]}
    text, metadata = build_message_metadata("<b>hi</b> &amp; <i>there</i>", parse_mode="html")
    assert text == "hi & there"
    assert [part["type"] for part in metadata["meta_data_parts"]] == ["Bold", "Italic"]
    assert metadata["meta_data_parts"][1] == {"type": "Italic", "from_index": 5, "length": 5}
    text, metadata = build_message_metadata("plain", entities=[MessageEntity.bold(0, 5)])
    assert metadata == {"meta_data_parts": [{"type": "Bold", "from_index": 0, "length": 5}]}
    assert build_message_metadata("plain") == ("plain", None)
    assert build_message_metadata(None) == (None, None)
    with pytest.raises(ValueError):
        build_message_metadata("x", entities=[MessageEntity.bold(0, 1)], parse_mode="markdown")
    with pytest.raises(ValueError):
        build_message_metadata("x", parse_mode="rst")
    assert parse_markdown("__it__")[1][0].type is MessageEntityType.ITALIC
    assert parse_html("<code>x</code>")[1][0].type is MessageEntityType.MONO


def test_updated_parameters_settings_and_file_builders():
    values, names = build_updated_parameters({"title": "T", "description": None, "slow_mode": 10})
    assert values == {"title": "T", "slow_mode": 10} and names == ["title", "slow_mode"]
    with pytest.raises(ValueError):
        build_updated_parameters({"nope": 1}, allowed=("title",))
    assert build_settings_input({"show_my_phone_number": "Nobody"}) == {"settings": {"show_my_phone_number": "Nobody"}, "update_parameters": ["show_my_phone_number"]}
    with pytest.raises(ValueError):
        build_settings_input({"x": None})
    block = build_file_inline(file_id="1", dc_id="2", access_hash_rec="r", file_name="a.mp4", size=10, media_type="Video", mime="mp4", width=1, height=2, duration_ms=3000, extra={"is_round": True, "skip": None})
    assert block["time"] == 3000 and block["is_round"] is True and "skip" not in block and block["type"] == "Video"
    assert guess_upload_mime("photo.JPEG") == "jpg" and guess_upload_mime("clip.mp4") == "mp4" and guess_upload_mime("noext") == "bin"


def test_envelope_builders_match_the_web_client():
    client = build_web_client_info()
    assert client == {"app_name": "Main", "app_version": "4.4.34", "platform": "Web", "package": "web.rubika.ir", "lang_code": "fa"}
    assert build_service_client_info() == {"app_name": "Main", "app_version": "4.4.34", "platform": "PWA", "package": "web.rubika.ir"}
    assert build_data_object("getUserInfo", {"user_guid": "u"}, client) == {"method": "getUserInfo", "input": {"user_guid": "u"}, "client": client}
    plain = build_plain_payload("getBaseInfo", {}, api_version="0", client_info=build_service_client_info(), auth="a")
    assert plain == {"method": "getBaseInfo", "api_version": "0", "data": {}, "client": build_service_client_info(), "auth": "a"}
