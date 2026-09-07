"""Client lifecycle, the invoke seam, login, updates and the typed mixins (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rubigram import Client, Transport, errors, types
from rubigram.enums import DcType
from rubigram.raw.methods import GetUserInfo
from rubigram.types import UserInfo

from .fake_rubika import (
    FAKE_AUTH,
    FAKE_CODE,
    FAKE_PHONE,
    FAKE_USER_GUID,
    FakeRubika,
    fixture,
    install,
    rsa_wrap,
    run,
    seed_session,
)


def make_client(**kwargs) -> Client:
    defaults = dict(in_memory=True, interactive=False, enable_socket=False, transport="http")
    defaults.update(kwargs)
    return Client("test", **defaults)


async def started(monkeypatch, **kwargs):
    rubika, services = install(monkeypatch)
    client = make_client(**kwargs)
    await seed_session(client)
    await client.start()
    return client, rubika, services


# ---------------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------------


def test_start_restores_session_discovers_dcs_and_refreshes_base_info(monkeypatch):
    async def scenario():
        client, rubika, services = await started(monkeypatch)
        assert client.is_connected and not client.is_bot
        assert client.dc.api_urls == ["https://messengerg2c777.iranlms.ir", "https://messengerg2c888.iranlms.ir"]
        assert client.dc.storage_url(491) == "https://messanger491.iranlms.ir/GetFile.ashx"
        # the base info refresh is a plain-JSON service call carrying the auth and the PWA client block
        method, payload, url = services.calls[0]
        assert method == "getBaseInfo" and payload["auth"] == FAKE_AUTH and payload["client"]["platform"] == "PWA"
        assert url == "https://servicesbase.iranlms.ir/"
        assert client.dc.urls(DcType.RUBINO) == ["https://rubino1.iranlms.ir"]
        # a registered device is not registered twice
        assert "registerDevice" not in rubika.methods()
        assert client._listener_task is None  # no handlers → nothing polls in the background
        assert "mode=user" in repr(client) and "transport=http" in repr(client)
        await client.stop()
        assert not client.is_connected and rubika.closed and services.closed
        await client.stop()  # idempotent

    run(scenario())


def test_context_manager_and_from_session_string(monkeypatch):
    async def real_scenario():
        install(monkeypatch)
        client = make_client()
        await seed_session(client)
        async with client as app:
            assert app is client and client.is_connected
            session_string = await client.export_session_string()
        assert not client.is_connected
        assert session_string.startswith("rbg2.")
        restored = Client.from_session_string("copy", session_string, interactive=False, enable_socket=False, transport="http")
        await restored.storage.open()
        assert await restored.storage.auth() == FAKE_AUTH
        assert await restored.storage.user_guid() == FAKE_USER_GUID
        await restored.storage.close()

    run(real_scenario())


def test_transport_mode_switching_and_temporary_override(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch, transport=Transport.WS)
        assert client.transport is Transport.WS
        client.set_transport("http")
        assert client.transport is Transport.HTTP
        async with client.use_transport("ws"):
            assert client.transport is Transport.WS
        assert client.transport is Transport.HTTP
        with pytest.raises(ValueError):
            client.set_transport("carrier-pigeon")
        await client.stop()

    run(scenario())


# ---------------------------------------------------------------------------
# invoke seam
# ---------------------------------------------------------------------------


def test_invoke_sends_signed_envelope_and_parses_typed_result(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        info = await client.get_user_info("u0EXAMPLE00000000000000000000008")
        assert isinstance(info, UserInfo)
        assert info.user.first_name == "Sample" and info.chat.object_guid == info.user.user_guid
        method, input_data = rubika.calls[-1]
        assert method == "getUserInfo" and input_data == {"user_guid": "u0EXAMPLE00000000000000000000008"}
        envelope = rubika.envelopes[-1]
        assert envelope["client"] == {"app_name": "Main", "app_version": "4.4.34", "platform": "Web", "package": "web.rubika.ir", "lang_code": "fa"}
        payload = rubika.payloads[-1]
        assert payload["api_version"] == "6" and set(payload) == {"api_version", "auth", "data_enc", "sign"}
        assert payload["auth"] != FAKE_AUTH  # caesar-encoded on the wire
        # the same thing through the raw layer
        same = await client.invoke(GetUserInfo(user_guid="u0EXAMPLE00000000000000000000008"))
        assert same.user.user_guid == info.user.user_guid
        await client.stop()

    run(scenario())


def test_invoke_raw_calls_any_method_by_name(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses["getSomethingNew"] = {"answer": 42}
        result = await client.invoke_raw("getSomethingNew", {"x": 1})
        assert isinstance(result, types.RawObject) and result.answer == 42
        assert rubika.calls[-1] == ("getSomethingNew", {"x": 1})
        await client.stop()

    run(scenario())


def test_not_registered_triggers_register_device_once_and_retries(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses["getChats"] = [{"status": "ERROR_GENERIC", "status_det": "NOT_REGISTERED"}, {"chats": [], "has_continue": False}]
        result = await client.get_chats()
        assert result.chats == [] and rubika.methods()[-3:] == ["getChats", "registerDevice", "getChats"]
        register = rubika.inputs("registerDevice")[0]
        assert register["token_type"] == "Web" and register["app_version"] == "WB_4.4.34" and register["token"] == ""
        assert register["device_hash"] and register["system_version"] == "Windows 10"
        assert await client.storage.registered_device() is True
        # a second NOT_REGISTERED in a row is surfaced, not retried forever
        rubika.responses["getChats"] = [{"status": "ERROR_GENERIC", "status_det": "NOT_REGISTERED"}] * 2
        with pytest.raises(errors.NotRegistered):
            await client.get_chats()
        await client.stop()

    run(scenario())


def test_rpc_errors_are_mapped_to_typed_exceptions(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses["getChats"] = {"status": "ERROR_ACTION", "status_det": "INVALID_AUTH"}
        with pytest.raises(errors.InvalidAuth) as info:
            await client.get_chats()
        assert info.value.is_session_dead and info.value.method == "getChats"
        rubika.responses["getChats"] = {"status": "ERROR_GENERIC", "status_det": "TOO_REQUESTS", "client_show_message": {"link": {"alert_data": {"message": "لطفا ۳۰ ثانیه دیگر تلاش کنید"}}}}
        with pytest.raises(errors.TooRequests) as info:
            await client.get_chats()
        assert info.value.retry_after == 30
        rubika.responses["getChats"] = FakeRubika.Outer({"status": "ERROR_ACTION", "status_det": "NOT_SUPPORTED_API_VERSION"})
        with pytest.raises(errors.NotSupportedApiVersion):
            await client.get_chats()
        rubika.responses["getChats"] = {"status": "ERROR_GENERIC", "status_det": "INVALID_INPUT"}
        with pytest.raises(errors.InvalidInput):
            await client.get_chats()
        await client.stop()

    run(scenario())


def test_user_methods_require_a_started_user_session(monkeypatch):
    async def scenario():
        install(monkeypatch)
        client = make_client()
        with pytest.raises(errors.AuthError):
            await client.get_chats()
        await client.storage.open()
        await client.start()  # no auth, non-interactive → started but not logged in
        assert client.is_connected
        with pytest.raises(errors.LoginRequired):
            await client.get_chats()
        await client.stop()

    run(scenario())


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


def test_login_flow_uses_tmp_session_then_stores_unwrapped_auth(monkeypatch):
    async def scenario():
        rubika, services = install(monkeypatch)
        client = make_client(phone_number=FAKE_PHONE, code_callback=lambda sent: FAKE_CODE)
        new_auth = "b" * 32

        rubika.responses["sendCode"] = {"status": "OK", "phone_code_hash": "hash-1", "code_digits_count": 5, "send_type": "SMS"}
        # the fake answers synchronously, so create the login key pair up front and wrap the auth with it
        await client.storage.open()
        await client._ensure_login_key_pair()
        public_key = await client.storage.public_key()
        rubika.responses["signIn"] = {"status": "OK", "auth": rsa_wrap(public_key, new_auth), "user_guid": FAKE_USER_GUID, "user": {"user_guid": FAKE_USER_GUID, "first_name": "Sample"}}
        rubika.auth = new_auth  # registerDevice afterwards is encrypted with the new session

        await client.start()
        assert rubika.methods() == ["sendCode", "signIn", "registerDevice"]
        send_payload, sign_payload = rubika.payloads[0], rubika.payloads[1]
        assert set(send_payload) == {"api_version", "tmp_session", "data_enc"} and send_payload["tmp_session"] == sign_payload["tmp_session"]
        assert rubika.inputs("sendCode")[0] == {"phone_number": FAKE_PHONE, "send_type": "SMS"}
        sign_in = rubika.inputs("signIn")[0]
        assert sign_in["phone_code"] == FAKE_CODE and sign_in["phone_code_hash"] == "hash-1" and sign_in["public_key"] == public_key
        assert await client.storage.auth() == new_auth
        assert await client.storage.tmp_session() is None
        assert await client.storage.user_guid() == FAKE_USER_GUID and client.user_guid == FAKE_USER_GUID
        assert await client.storage.registered_device() is True
        await client.stop()

    run(scenario())


def test_login_retries_invalid_codes_and_handles_two_step(monkeypatch):
    async def scenario():
        rubika, _ = install(monkeypatch)
        codes = iter(["11111", FAKE_CODE])
        client = make_client()
        await client.storage.open()
        await client.start()
        await client._ensure_login_key_pair()
        public_key = await client.storage.public_key()
        rubika.responses["sendCode"] = [
            {"status": "SendPassKey", "hint": "pet"},
            {"status": "OK", "phone_code_hash": "hash-2", "code_digits_count": 5},
        ]
        rubika.responses["signIn"] = [
            {"status": "CodeIsInvalid"},
            {"status": "OK", "auth": rsa_wrap(public_key, "c" * 32), "user_guid": FAKE_USER_GUID},
        ]
        rubika.auth = "c" * 32
        authorization = await client.login(FAKE_PHONE, code_callback=lambda sent: next(codes), password="secret-word")
        assert authorization.user_guid == FAKE_USER_GUID
        assert rubika.inputs("sendCode")[1]["pass_key"] == "secret-word"
        assert [item["phone_code"] for item in rubika.inputs("signIn")] == ["11111", FAKE_CODE]
        # once logged in, login() is a no-op
        assert (await client.login()).user_guid == FAKE_USER_GUID
        await client.stop()

    run(scenario())


def test_login_without_credentials_fails_loudly_when_not_interactive(monkeypatch):
    async def scenario():
        install(monkeypatch)
        client = make_client()
        await client.start()
        with pytest.raises(errors.LoginRequired):
            await client.login()
        await client.stop()

    run(scenario())


def test_logout_clears_auth(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses["logout"] = {}
        await client.logout()
        assert rubika.methods()[-1] == "logout" and await client.storage.auth() is None
        await client.stop()

    run(scenario())


# ---------------------------------------------------------------------------
# messages, chats and users
# ---------------------------------------------------------------------------


def test_send_message_builds_metadata_rnd_and_returns_sent_message(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        sent = await client.send_message("u0EXAMPLE00000000000000000000002", "**bold** text", parse_mode="markdown", reply_to_message_id="10")
        assert isinstance(sent, types.SentMessage) and sent.message_id == "1547993674553407" and sent.message.text == "sample text"
        input_data = rubika.inputs("sendMessage")[0]
        assert input_data["text"] == "bold text" and input_data["rnd"].isdigit() and input_data["reply_to_message_id"] == "10"
        assert input_data["metadata"] == {"meta_data_parts": [{"type": "Bold", "from_index": 0, "length": 4}]}
        # legacy positional (guid, rnd, text) still works with a warning
        with pytest.warns(DeprecationWarning):
            await client.send_message("u0EXAMPLE00000000000000000000002", "123456", "hello")
        assert rubika.inputs("sendMessage")[1]["text"] == "hello" and rubika.inputs("sendMessage")[1]["rnd"] == "123456"
        await client.stop()

    run(scenario())


def test_message_helpers_map_to_the_right_rpcs(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses.update({"editMessage": {}, "deleteMessages": {}, "forwardMessages": {}, "setPinMessage": {}, "getMessages": {"messages": [{"message_id": "5", "text": "x"}, {"message_id": "4"}], "has_continue": True}, "getMessagesByID": {"messages": [{"message_id": "7", "text": "seven"}]}, "actionOnMessageReaction": {}, "createPoll": {}})
        await client.edit_message("g1", "1", "new __text__", parse_mode="markdown")
        await client.delete_message("g1", "1")
        await client.delete_messages("g1", ["1", 2], delete_type="Local")
        await client.forward_message("g1", "1", "g2")
        await client.pin_message("g1", "1")
        await client.unpin_message("g1", "1")
        await client.react("g1", "1", 3)
        await client.create_poll("g1", "Q?", ["a", "b"], poll_type="Quiz", correct_option_index=1)
        message = await client.get_message("g1", "7")
        assert message.text == "seven" and message.object_guid == "g1"
        page = await client.get_messages("g1", max_id="10", limit=2)
        assert [m.message_id for m in page.messages] == ["5", "4"]
        assert rubika.inputs("editMessage")[0] == {"object_guid": "g1", "message_id": "1", "text": "new text", "metadata": {"meta_data_parts": [{"type": "Italic", "from_index": 4, "length": 4}]}}
        assert rubika.inputs("deleteMessages") == [{"object_guid": "g1", "message_ids": ["1"], "type": "Global"}, {"object_guid": "g1", "message_ids": ["1", "2"], "type": "Local"}]
        forward = rubika.inputs("forwardMessages")[0]
        assert forward["from_object_guid"] == "g1" and forward["to_object_guid"] == "g2" and forward["message_ids"] == ["1"]
        assert [item["action"] for item in rubika.inputs("setPinMessage")] == ["Pin", "Unpin"]
        assert rubika.inputs("actionOnMessageReaction")[0] == {"object_guid": "g1", "message_id": "1", "reaction_id": 3, "action": "Add"}
        poll = rubika.inputs("createPoll")[0]
        assert poll["type"] == "Quiz" and poll["correct_option_index"] == 1 and poll["options"] == ["a", "b"] and poll["is_anonymous"] is True
        assert rubika.inputs("getMessages")[0] == {"object_guid": "g1", "max_id": "10", "sort": "FromMax", "limit": 2}
        # bound helpers on the typed objects go through the same client
        await message.delete()
        assert rubika.inputs("deleteMessages")[-1]["message_ids"] == ["7"]
        await client.stop()

    run(scenario())


def test_iter_messages_pages_backwards(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses["getMessages"] = [
            {"messages": [{"message_id": "30"}, {"message_id": "29"}], "has_continue": True},
            {"messages": [{"message_id": "28"}], "has_continue": False},
        ]
        ids = [m.message_id async for m in client.iter_messages("g1", page_size=2)]
        assert ids == ["30", "29", "28"]
        assert rubika.inputs("getMessages")[1]["max_id"] == "28"
        await client.stop()

    run(scenario())


def test_chats_and_users_mixins(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses.update({"getChats": {"chats": [{"object_guid": "g1", "last_message": {"message_id": "1"}}], "has_continue": False}, "setActionChat": {}, "setBlockUser": {}, "getContactsUpdates": {"new_state": 99, "users": []}, "updateProfile": {}})
        chats = await client.get_chats()
        assert chats.chats[0].last_message.object_guid == "g1"
        await client.mute_chat("g1", duration=60)
        await client.block_user("u1")
        await client.unblock_user(peer="u2")
        await client.seen("g1", "1")
        await client.update_profile(first_name="A", bio=None)
        assert rubika.inputs("setActionChat")[0] == {"object_guid": "g1", "action": "Mute", "duration": 60}
        assert [item["action"] for item in rubika.inputs("setBlockUser")] == ["Block", "Unblock"]
        assert rubika.inputs("seenChats")[0] == {"seen_list": {"g1": "1"}}
        assert rubika.inputs("updateProfile")[0] == {"first_name": "A", "updated_parameters": ["first_name"]}
        with pytest.raises(ValueError):
            await client.update_profile()
        updates = await client.get_contacts_updates()
        assert updates.new_state == 99 and await client.storage.contacts_state() == 99
        chat = await client.get_chat("u0EXAMPLE00000000000000000000001")
        assert isinstance(chat, types.Chat) and chat.object_guid == "u0EXAMPLE00000000000000000000001"
        me = await client.get_me()
        assert isinstance(me, UserInfo) and rubika.inputs("getUserInfo")[-1] == {"user_guid": FAKE_USER_GUID}
        await client.stop()

    run(scenario())


def test_groups_channels_and_join_links(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses.update({"leaveGroup": {}, "joinGroup": {}, "joinChannelAction": {}, "joinChannelByLink": {}, "editJoinLink": {}})
        info = await client.get_group_info("g0EXAMPLE00000000000000000000001")
        assert info.group.group_title and rubika.inputs("getGroupInfo")[0] == {"group_guid": "g0EXAMPLE00000000000000000000001"}
        await client.edit_group_info("g1", title="T", slow_mode=10)
        assert rubika.inputs("editGroupInfo")[0] == {"group_guid": "g1", "title": "T", "slow_mode": 10, "updated_parameters": ["title", "slow_mode"]}
        await client.set_group_admin("g1", "u1", ["PinMessages", "DeleteGlobalAllMessages"])
        assert rubika.inputs("setGroupAdmin")[0]["access_list"] == ["PinMessages", "DeleteGlobalAllMessages"]
        await client.join_group("https://rubika.ir/joing/ABCDEF0123456789ABCDEF0123456789")
        assert rubika.inputs("joinGroup")[0] == {"hash_link": "ABCDEF0123456789ABCDEF0123456789"}
        await client.join_channel("c1")
        await client.join_channel("https://rubika.ir/joinc/ABCDEF0123456789ABCDEF0123456789")
        assert rubika.inputs("joinChannelAction")[0] == {"channel_guid": "c1", "action": "Join"}
        assert rubika.inputs("joinChannelByLink")[0] == {"hash_link": "ABCDEF0123456789ABCDEF0123456789"}
        await client.leave_channel("c1")
        assert rubika.inputs("joinChannelAction")[1]["action"] == "Leave"
        link = await client.create_join_link("g1", "invite", usage_limit=5)
        assert link.join_link.title == "team" or link.join_link is not None
        assert rubika.inputs("createJoinLink")[0] == {"object_guid": "g1", "title": "invite", "request_needed": False, "expire_time": 0, "usage_limit": 5}
        await client.edit_join_link("g1", "https://rubika.ir/joing/X", usage_limit=1)
        assert rubika.inputs("editJoinLink")[0]["updated_parameters"] == ["usage_limit"]
        await client.stop()

    run(scenario())


# ---------------------------------------------------------------------------
# media
# ---------------------------------------------------------------------------


class StubUpload:
    def __init__(self):
        self.calls = []

    async def upload_file(self, *, auth, descriptor, path=None, data=None, progress=None, progress_args=()):
        self.calls.append({"auth": auth, "descriptor": descriptor, "path": path, "data": data})
        descriptor.access_hash_rec = "rec-hash"
        return descriptor

    async def close(self):
        pass


class StubDownload:
    def __init__(self):
        self.calls = []

    async def download_file(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("in_memory"):
            return b"bytes"
        Path(kwargs["path"]).write_bytes(b"bytes")
        return Path(kwargs["path"])

    async def download_url(self, **kwargs):
        self.calls.append(kwargs)
        return b"url-bytes"

    async def close(self):
        pass


def test_send_media_requests_slot_uploads_then_sends_file_inline(monkeypatch, tmp_path):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        client._upload = StubUpload()
        photo = tmp_path / "pic.jpg"
        photo.write_bytes(b"\xff\xd8" * 10)
        sent = await client.send_photo("g1", photo, text="caption", width=10, height=20)
        assert isinstance(sent, types.SentMessage)
        request = rubika.inputs("requestSendFile")[0]
        assert request == {"file_name": "pic.jpg", "size": 20, "mime": "jpg"}
        upload = client._upload.calls[0]
        assert upload["auth"] == FAKE_AUTH and upload["descriptor"].upload_url.startswith("https://upmessenger491")
        message = rubika.inputs("sendMessage")[0]
        assert message["text"] == "caption" and message["file_inline"]["type"] == "Image"
        assert message["file_inline"]["file_id"] == "87998036915657" and message["file_inline"]["dc_id"] == "491" and message["file_inline"]["access_hash_rec"] == "rec-hash"
        assert message["file_inline"]["width"] == 10 and message["file_inline"]["height"] == 20 and message["file_inline"]["size"] == 20
        with pytest.raises(ValueError):
            await client.send_voice("g1", photo)  # duration unknown for a non-ogg file
        await client.stop()

    run(scenario())


def test_download_file_uses_the_storage_of_the_dc(monkeypatch, tmp_path):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        client._download = StubDownload()
        message = types.Message(client=client, message_id="1", file_inline=types.FileInline(client=client, file_id="f1", dc_id="491", access_hash_rec="r", file_name="a.bin", size="3"))
        target = await client.download_file(message, tmp_path)
        assert target == tmp_path / "a.bin" and target.read_bytes() == b"bytes"
        call = client._download.calls[0]
        assert call["url"] == "https://messanger491.iranlms.ir/GetFile.ashx" and call["auth"] == FAKE_AUTH and call["file_size"] == 3
        data = await message.download(in_memory=True)
        assert data == b"bytes"
        assert await client.download_url("https://cdn.example/x.jpg", in_memory=True) == b"url-bytes"
        with pytest.raises(ValueError):
            await client.download_file(types.Message(client=client, message_id="2"))
        await client.stop()

    run(scenario())


# ---------------------------------------------------------------------------
# updates over HTTP, rubino, sessions
# ---------------------------------------------------------------------------


def test_get_updates_over_http_persists_state_and_ignores_old_state(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        result = await client.get_updates()
        assert isinstance(result, types.ChatsUpdates) and result.new_state == 1773595460
        assert await client.storage.updates_state() == 1773595460
        rubika.responses["getChatsUpdates"] = {"status": "OldState", "chats": [], "new_state": 5}
        old = await client.get_chats_updates()
        assert old.is_old_state and await client.storage.updates_state() == 1773595460
        assert rubika.inputs("getChatsUpdates")[1] == {"state": 1773595460}
        await client.stop()

    run(scenario())


def test_rubino_post_goes_to_the_suggested_rubino_url(monkeypatch):
    async def scenario():
        client, rubika, services = await started(monkeypatch)
        services.responses["getProfilePosts"] = {"status": "OK", "data": {"posts": [{"id": "p1", "profile_id": "pr1", "post_type": "Picture", "full_file_url": "https://cdn/x.jpg"}]}}
        result = await client.get_rubino_post("p1", "pr1")
        assert result.posts[0].id == "p1" and result.posts[0].full_file_url.endswith("x.jpg")
        method, payload, url = services.calls[-1]
        assert method == "getProfilePosts" and url == "https://rubino1.iranlms.ir/"
        assert payload["api_version"] == "0" and payload["auth"] == FAKE_AUTH and payload["client"]["platform"] == "PWA"
        assert payload["data"] == {"target_profile_id": "pr1", "max_id": "p1", "min_id": "p1", "equal": True, "limit": 1, "sort": "FromMax"}
        with pytest.raises(ValueError):
            await client.get_rubino_post()
        await client.stop()

    run(scenario())


def test_sessions_mixin_and_session_dict(monkeypatch):
    async def scenario():
        client, rubika, _ = await started(monkeypatch)
        rubika.responses["getMySessions"] = {"sessions": [{"key": "k1", "app_version": "WB_4.4.34"}]}
        rubika.responses["terminateSession"] = {}
        sessions = await client.get_my_sessions()
        assert sessions.sessions[0].key == "k1"
        await client.terminate_session("k1")
        assert rubika.inputs("terminateSession")[0] == {"session_key": "k1"}
        exported = await client.export_session_dict()
        assert exported["auth"] == FAKE_AUTH and exported["user_guid"] == FAKE_USER_GUID
        await client.stop()

    run(scenario())
