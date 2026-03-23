import asyncio
import base64
import uuid
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

import rubigram.client as client_module
from rubigram import filters
from rubigram.enums import GroupAdminAccess, GroupDefaultAccessPermission
from rubigram.client import Client
from rubigram.crypto import encrypt_aes_cbc, export_public_key_for_login, rsa_key_generate
from rubigram.errors import InvalidInput as ErrorsInvalidInput
from rubigram.exceptions import AuthKeyInvalid, CodeIsInvalid, InvalidInput, LoginRequired, RegisterDeviceRequired
from rubigram.raw.methods import AddChannelMembers, AddGroupMembers, DeleteChatHistory, GetBannedChannelMembers, GetChannelAdminMembers, GetChannelAllMembers, GetChannelInfo, GetChannelLink, GetProfileLinkItems, GetUserInfo, SearchGlobalObjects, SendChatActivity, UploadNewGroupAvatar
from rubigram.storage import MemoryStorage
from rubigram.types import Message


def encrypt_response(data, request_key):
    return {
        "status": "OK",
        "status_det": "OK",
        "data_enc": encrypt_aes_cbc(data, request_key),
    }


async def fake_fetch_dcs(self):
    return {
        "status": "OK",
        "status_det": "OK",
        "data": {
            "default_api_urls": [
                "https://messengerg2c513.iranlms.ir",
                "https://messengerg2c466.iranlms.ir",
            ],
            "storages": {},
            "default_cdn_urls": {},
            "default_sockets": [],
        },
    }


def test_client_start_refreshes_dc_config(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        assert await client.storage.api_urls() == [
            "https://messengerg2c513.iranlms.ir",
            "https://messengerg2c466.iranlms.ir",
        ]
        assert await client.storage.api_url() == "https://messengerg2c513.iranlms.ir"

        await client.stop()

    asyncio.run(scenario())


def test_client_start_runs_interactive_authorize_when_needed(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        monkeypatch.setattr(Client, "_should_interactive_authorize", lambda self: True)

        async def fake_authorize(self):
            await self.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")
            await self.storage.set_user_guid("u0test")
            return {"user": {"user_guid": "u0test"}}

        monkeypatch.setattr(Client, "authorize", fake_authorize)

        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        assert await client.storage.auth() == "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
        assert await client.storage.user_guid() == "u0test"

        await client.stop()

    asyncio.run(scenario())


def test_phone_number_with_plus_is_not_detected_as_bot_token():
    client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)

    assert client._normalize_phone_number("+989912123456") == "989912123456"
    assert client._looks_like_phone_number_input("+989912123456")
    assert not client._looks_like_bot_token("+989912123456")


def test_phone_number_with_common_separators_is_not_detected_as_bot_token():
    client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)

    assert client._normalize_phone_number("09 912-123-456") == "98912123456"
    assert client._looks_like_phone_number_input("09 912-123-456")
    assert not client._looks_like_bot_token("09 912-123-456")


def test_client_start_refreshes_legacy_public_key(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        public_key, private_pem = rsa_key_generate()
        legacy_public_key = base64.b64encode(
            serialization.load_pem_private_key(
                private_pem.encode("utf-8"),
                password=None,
                backend=default_backend(),
            ).public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).strip()
        ).decode("utf-8")

        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_private_key_pem(private_pem)
        await client.storage.set_public_key(legacy_public_key)
        await client._ensure_login_key_pair()

        assert await client.storage.public_key() == export_public_key_for_login(private_pem)
        assert await client.storage.public_key() == public_key

        await client.stop()

    asyncio.run(scenario())


def test_client_start_performs_socket_handshake_when_auth_exists(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)

        calls = []

        async def fake_handshake(self, auth, api_version="5", force_reconnect=False):
            calls.append({
                "auth": auth,
                "api_version": api_version,
                "force_reconnect": force_reconnect,
            })
            return {"status": "OK", "status_det": "OK"}

        monkeypatch.setattr(client_module.SocketTransport, "handshake", fake_handshake)

        bootstrap = MemoryStorage("bootstrap")
        await bootstrap.open()
        await bootstrap.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")
        session_string = await bootstrap.export_session_string()
        await bootstrap.close()

        client = Client("test", session_string=session_string, enable_register_device=False)

        await client.start()

        assert calls == [{
            "auth": "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb",
            "api_version": "5",
            "force_reconnect": False,
        }]

        await client.stop()

    asyncio.run(scenario())


def test_invoke_requires_auth_for_authenticated_methods(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        try:
            await client.invoke(GetUserInfo(user_guid="u123"))
        except LoginRequired:
            pass
        else:
            raise AssertionError("Expected LoginRequired")

        await client.stop()

    asyncio.run(scenario())


def test_invoke_ensures_socket_handshake_for_authenticated_methods(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        calls = []

        async def fake_handshake(self, auth, api_version="5", force_reconnect=False):
            calls.append((auth, api_version, force_reconnect))
            return {"status": "OK", "status_det": "OK"}

        monkeypatch.setattr(client_module.SocketTransport, "handshake", fake_handshake)

        async def send_payload(payload):
            auth = await client.storage.auth()
            return encrypt_response({"status": "OK", "status_det": "OK", "data": {"user_guid": "u1"}}, auth)

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.invoke(GetUserInfo(user_guid="u1"))

        assert result.user_guid == "u1"
        assert calls == [("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb", "5", False)]

        await client.stop()

    asyncio.run(scenario())


def test_send_code_creates_tmp_session_lazily(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        async def send_payload(payload):
            assert payload["api_version"] == "6"
            assert "sign" not in payload
            assert "auth" not in payload
            assert "data_enc" in payload
            assert "tmp_session" in payload
            decrypted = encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {"status": "OK", "phone_code_hash": "hash-1"},
                },
                payload["tmp_session"],
            )
            return {"data_enc": decrypted["data_enc"]}

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.send_code("989121234567")

        assert result.phone_code_hash == "hash-1"
        assert await client.storage.tmp_session() is not None

        await client.stop()

    asyncio.run(scenario())


def test_send_code_normalizes_phone_number(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        async def send_payload(payload):
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, payload["tmp_session"])
            assert decrypted_request["input"]["phone_number"] == "989121234567"
            decrypted = encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {"status": "OK", "phone_code_hash": "hash-1"},
                },
                payload["tmp_session"],
            )
            return {"data_enc": decrypted["data_enc"]}

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.send_code("+98912 123 4567")
        assert result.phone_code_hash == "hash-1"

        await client.stop()

    asyncio.run(scenario())


def test_sign_in_stores_auth_and_clears_tmp_session(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        private_key_pem = await client.storage.private_key_pem()
        session_public_key = await client.storage.public_key()
        assert private_key_pem is not None
        assert session_public_key is not None

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
            backend=default_backend(),
        )
        public_key = private_key.public_key()
        expected_auth = "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
        encrypted_auth = base64.b64encode(
            public_key.encrypt(expected_auth.encode("utf-8"), asym_padding.PKCS1v15())
        ).decode("utf-8")

        async def send_payload(payload):
            assert payload["api_version"] == "6"
            assert "sign" not in payload
            assert "auth" not in payload
            assert "data_enc" in payload
            assert "tmp_session" in payload
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, payload["tmp_session"])
            assert decrypted_request["input"]["public_key"] == session_public_key
            decrypted = encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "status": "OK",
                        "auth": encrypted_auth,
                        "user": {"user_guid": "u0DiqTP0d4d36e090fb7060d540a33c7"},
                    },
                },
                payload["tmp_session"],
            )
            return {"data_enc": decrypted["data_enc"]}

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        await client.sign_in(
            phone_number="989121234567",
            phone_code_hash="hash-1",
            phone_code="123456",
        )

        assert await client.storage.auth() == expected_auth
        assert await client.storage.tmp_session() is None
        assert await client.storage.public_key() == session_public_key
        assert await client.storage.user_guid() == "u0DiqTP0d4d36e090fb7060d540a33c7"

        await client.stop()

    asyncio.run(scenario())


def test_authorize_formats_invalid_input_error(monkeypatch):
    client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
    error = InvalidInput("ERROR_GENERIC", "INVALID_INPUT")

    assert client._format_authorize_error(error, stage="phone_number").startswith("The server rejected the phone number input.")
    assert "public_key/changeAuthType" in client._format_authorize_error(error, stage="phone_code")


def test_errors_package_re_exports_exceptions():
    assert ErrorsInvalidInput is InvalidInput


def test_invoke_raises_for_outer_and_inner_errors(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def outer_error(payload):
            return {"status": "INVALID_AUTH", "status_det": "AUTH_INVALID"}

        client._transport.send_payload = outer_error  # type: ignore[method-assign]

        try:
            await client.invoke(GetUserInfo(user_guid="u123"))
        except AuthKeyInvalid:
            pass
        else:
            raise AssertionError("Expected AuthKeyInvalid")

        async def inner_error(payload):
            auth = await client.storage.auth()
            return encrypt_response({"status": "CODE_INVALID", "status_det": "CODE_INVALID"}, auth)

        client._transport.send_payload = inner_error  # type: ignore[method-assign]

        try:
            await client.invoke(GetUserInfo(user_guid="u123"))
        except CodeIsInvalid:
            pass
        else:
            raise AssertionError("Expected CodeIsInvalid")

        await client.stop()

    asyncio.run(scenario())


def test_not_registered_maps_to_register_device_required(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def not_registered(payload):
            auth = await client.storage.auth()
            return encrypt_response({"status": "ERROR_ACTION", "status_det": "NOT_REGISTERED"}, auth)

        client._transport.send_payload = not_registered  # type: ignore[method-assign]

        try:
            await client.invoke(GetUserInfo(user_guid="u123"))
        except RegisterDeviceRequired:
            pass
        else:
            raise AssertionError("Expected RegisterDeviceRequired")

        await client.stop()

    asyncio.run(scenario())


def test_register_device_uses_expected_web_payload(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "registerDevice"
            assert decrypted_request["input"]["token_type"] == "Web"
            assert decrypted_request["input"]["token"] == ""
            assert decrypted_request["input"]["app_version"] == "WB_4.4.27"
            assert decrypted_request["input"]["lang_code"] == "fa"
            assert decrypted_request["input"]["system_version"] == "Windows 10"
            assert decrypted_request["input"]["device_model"] == "Chrome 145"
            assert decrypted_request["input"]["device_hash"].isdigit()
            assert len(decrypted_request["input"]["device_hash"]) == 26
            return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        await client.register_device()

        assert await client.storage.registered_device() is True
        assert await client.storage.registered_device_version() == "4.4.27"
        assert await client.storage.device_hash() is not None

        await client.stop()

    asyncio.run(scenario())


def test_invoke_retries_after_register_device_flow(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")
        await client.storage.set_registered_device(True)
        await client.storage.set_registered_device_version("4.4.27")

        calls = []

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            calls.append(decrypted_request["method"])

            if decrypted_request["method"] == "getUserInfo" and len(calls) == 1:
                return encrypt_response({"status": "ERROR_ACTION", "status_det": "NOT_REGISTERED"}, auth)
            if decrypted_request["method"] == "registerDevice":
                return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)
            if decrypted_request["method"] == "getUserInfo" and len(calls) == 3:
                return encrypt_response({"status": "OK", "status_det": "OK", "data": {"user_guid": "u123"}}, auth)

            raise AssertionError(f"Unexpected method order: {calls}")

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.invoke(GetUserInfo(user_guid="u123"))

        assert result.user_guid == "u123"
        assert calls == ["getUserInfo", "registerDevice", "getUserInfo"]
        assert await client.storage.registered_device() is True

        await client.stop()

    asyncio.run(scenario())


def test_get_user_info_returns_typed_classes(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "_": "UserInfo",
                        "user": {
                            "_": "User",
                            "user_guid": "u123",
                            "first_name": "King",
                            "last_name": "Smith",
                            "phone": "989912398434",
                            "username": "king",
                            "last_online": 1773593199,
                            "is_deleted": False,
                            "is_verified": True,
                            "online_time": {"type": "Exact", "exact_time": 1773593199},
                            "avatar_thumbnail": {
                                "_": "RawObject",
                                "file_id": "42",
                                "mime": "jpg",
                            },
                        },
                        "chat": {
                            "_": "Chat",
                            "object_guid": "u123",
                            "status": "Active",
                            "access": ["ViewInfo", "SendMessages"],
                            "avatar_thumbnail": {
                                "_": "RawObject",
                                "file_id": "84",
                                "mime": "jpg",
                                "dc_id": "465",
                                "access_hash_rec": "chat-rec",
                            },
                            "last_message": {
                                "_": "Message",
                                "message_id": "1",
                                "text": "hello",
                                "type": "Text",
                            },
                            "abs_object": {
                                "_": "PeerObject",
                                "object_guid": "u123",
                                "type": "User",
                            },
                            "auto_delete": "Off",
                        },
                        "timestamp": "1773593199",
                        "can_receive_call": True,
                        "can_video_call": True,
                        "user_additional_info": {
                            "_": "UserAdditionalInfo",
                            "is_in_contact": False,
                            "registration_time": 1646062372,
                            "country_code": "IR",
                        },
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_user_info("u123")

        assert result.user.user_guid == "u123"
        assert result.user.online_time.type == "Exact"
        assert result.user.avatar_thumbnail.file_id == "42"
        assert result.chat.object_guid == "u123"
        assert result.chat.access == ["ViewInfo", "SendMessages"]
        assert result.chat.avatar_thumbnail.file_id == "84"
        assert result.chat.last_message.text == "hello"
        assert result.chat.last_message.object_guid == "u123"
        assert result.chat.abs_object.type == "User"
        assert result.timestamp == "1773593199"
        assert result.can_receive_call is True
        assert result.can_video_call is True
        assert result.user_additional_info.is_in_contact is False
        assert result.user_additional_info.country_code == "IR"

        await client.stop()

    asyncio.run(scenario())


def test_get_user_info_raises_invalid_input_when_user_not_found(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            return encrypt_response({"status": "ERROR_GENERIC", "status_det": "INVALID_INPUT"}, auth)

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        try:
            await client.get_user_info("u404")
        except InvalidInput as exc:
            assert exc.status == "ERROR_GENERIC"
            assert exc.status_det == "INVALID_INPUT"
        else:
            raise AssertionError("Expected InvalidInput")

        await client.stop()

    asyncio.run(scenario())


def test_get_contacts_last_online_returns_typed_users(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getContactsLastOnline"
            assert decrypted_request["input"] == {
                "user_guids": [
                    "u0Br9G039b54b9d29b79b8a1748ddec5",
                    "u0IwXY40a6d324732ea2d4c162acf937",
                    "u0Fa5L1046a4027e57b6b6bb22086a85",
                ]
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "users": [
                            {
                                "user_guid": "u0Br9G039b54b9d29b79b8a1748ddec5",
                                "last_online": 1714941000,
                                "online_time": {
                                    "type": "Approximate",
                                    "approximate_period": "LongAgo",
                                },
                            },
                            {
                                "user_guid": "u0IwXY40a6d324732ea2d4c162acf937",
                                "last_online": 1714768200,
                                "online_time": {
                                    "type": "Approximate",
                                    "approximate_period": "LongAgo",
                                },
                            },
                        ]
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_contacts_last_online(
            [
                "u0Br9G039b54b9d29b79b8a1748ddec5",
                "u0IwXY40a6d324732ea2d4c162acf937",
                "u0Fa5L1046a4027e57b6b6bb22086a85",
            ]
        )

        assert len(result.users) == 2
        assert result.users[0].user_guid == "u0Br9G039b54b9d29b79b8a1748ddec5"
        assert result.users[0].last_online == 1714941000
        assert result.users[0].online_time is not None
        assert result.users[0].online_time.approximate_period == "LongAgo"
        assert result.users[1].user_guid == "u0IwXY40a6d324732ea2d4c162acf937"

        await client.stop()

    asyncio.run(scenario())


def test_avatar_thumbnail_download_delegates_to_client(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "user": {
                            "user_guid": "u123",
                            "avatar_thumbnail": {
                                "file_id": "42",
                                "mime": "jpg",
                                "dc_id": "464",
                                "access_hash_rec": "rec-hash",
                            },
                        },
                        "chat": {
                            "object_guid": "u123",
                            "avatar_thumbnail": {
                                "file_id": "84",
                                "mime": "jpg",
                                "dc_id": "465",
                                "access_hash_rec": "chat-rec",
                            },
                        },
                    },
                },
                auth,
            )

        captured = {}

        async def fake_download_file(file, path=None, *, in_memory=False, file_name=None, progress=None, progress_args=()):
            captured["file"] = file
            captured["path"] = path
            captured["in_memory"] = in_memory
            captured["file_name"] = file_name
            return b"avatar-bytes"

        client._transport.send_payload = send_payload  # type: ignore[method-assign]
        client.download_file = fake_download_file  # type: ignore[method-assign]

        result = await client.get_user_info("u123")
        avatar = result.user.avatar_thumbnail

        content = await avatar.download(in_memory=True, file_name="avatar.jpg")

        assert content == b"avatar-bytes"
        assert captured["file"] is avatar
        assert captured["in_memory"] is True
        assert captured["file_name"] == "avatar.jpg"

        chat_avatar = result.chat.avatar_thumbnail
        content = await chat_avatar.download(in_memory=True, file_name="chat-avatar.jpg")

        assert content == b"avatar-bytes"
        assert captured["file"] is chat_avatar
        assert captured["file_name"] == "chat-avatar.jpg"

        await client.stop()

    asyncio.run(scenario())


def test_chat_avatars_is_list_like_and_avatar_downloads_main_file(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "avatars": [
                            {
                                "avatar_id": "a1",
                                "thumbnail": {
                                    "file_id": "thumb-1",
                                    "mime": "jpg",
                                    "dc_id": "111",
                                    "access_hash_rec": "thumb-rec-1",
                                },
                                "main": {
                                    "file_id": "main-1",
                                    "mime": "jpg",
                                    "dc_id": "112",
                                    "access_hash_rec": "main-rec-1",
                                },
                            },
                            {
                                "avatar_id": "a2",
                                "thumbnail": {
                                    "file_id": "thumb-2",
                                    "mime": "jpg",
                                    "dc_id": "121",
                                    "access_hash_rec": "thumb-rec-2",
                                },
                                "main": {
                                    "file_id": "main-2",
                                    "mime": "jpg",
                                    "dc_id": "122",
                                    "access_hash_rec": "main-rec-2",
                                },
                            },
                        ]
                    },
                },
                auth,
            )

        captured = {}

        async def fake_download_file(file, path=None, *, in_memory=False, file_name=None, progress=None, progress_args=()):
            captured["file"] = file
            captured["file_name"] = file_name
            return b"avatar-main"

        client._transport.send_payload = send_payload  # type: ignore[method-assign]
        client.download_file = fake_download_file  # type: ignore[method-assign]

        avatars = await client.get_avatars("u123")

        assert len(avatars) == 2
        assert avatars[-1].avatar_id == "a2"

        content = await avatars[-1].download(in_memory=True, file_name="avatar.jpg")

        assert content == b"avatar-main"
        assert captured["file"] is avatars[-1].main
        assert captured["file_name"] == "avatar.jpg"

        await client.stop()

    asyncio.run(scenario())


def test_chat_avatars_download_downloads_all_with_generated_names(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "avatars": [
                            {
                                "avatar_id": "a1",
                                "main": {
                                    "file_id": "main-1",
                                    "mime": "jpg",
                                    "dc_id": "112",
                                    "access_hash_rec": "main-rec-1",
                                },
                            },
                            {
                                "avatar_id": "a2",
                                "main": {
                                    "file_id": "main-2",
                                    "mime": "png",
                                    "dc_id": "122",
                                    "access_hash_rec": "main-rec-2",
                                },
                            },
                        ]
                    },
                },
                auth,
            )

        calls = []

        async def fake_download_file(file, path=None, *, in_memory=False, file_name=None, progress=None, progress_args=()):
            calls.append({"file": file, "path": path, "file_name": file_name})
            return file_name

        client._transport.send_payload = send_payload  # type: ignore[method-assign]
        client.download_file = fake_download_file  # type: ignore[method-assign]

        avatars = await client.get_avatars("u123")
        result = await avatars.download(path="downloads")

        assert result == ["a1_main.jpg", "a2_main.png"]
        assert calls == [
            {"file": avatars[0].main, "path": "downloads", "file_name": "a1_main.jpg"},
            {"file": avatars[1].main, "path": "downloads", "file_name": "a2_main.png"},
        ]

        await client.stop()

    asyncio.run(scenario())


def test_get_me_uses_stored_user_guid(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")
        await client.storage.set_user_guid("u123")

        async def send_payload(payload):
            auth = await client.storage.auth()
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "user": {"user_guid": "u123", "first_name": "King"},
                        "chat": {"object_guid": "u123", "status": "Active"},
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_me()

        assert result.user.user_guid == "u123"
        assert result.user.first_name == "King"
        assert result.chat.object_guid == "u123"

        await client.stop()

    asyncio.run(scenario())


def test_get_chats_updates_uses_and_persists_state(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")
        await client.storage.set_updates_state(1773595399)

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getChatsUpdates"
            assert decrypted_request["input"]["state"] == 1773595399
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "chats": [],
                        "new_state": 1773595460,
                        "status": "OK",
                        "timestamp": "1773595520",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_chats_updates()

        assert result.new_state == 1773595460
        assert await client.storage.updates_state() == 1773595460

        await client.stop()

    asyncio.run(scenario())


def test_get_available_reactions_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getAvailableReactions"
            assert decrypted_request["input"] == {}
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "reactions": [
                            {
                                "reaction_id": "1",
                                "emoji_char": "❤",
                                "name": "Red Heart",
                            },
                            {
                                "reaction_id": "74",
                                "emoji_char": "🇮🇷",
                                "name": "Iran",
                            },
                        ],
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_available_reactions()

        assert len(result.reactions) == 2
        assert result.reactions[0].reaction_id == "1"
        assert result.reactions[0].emoji_char == "❤"
        assert result.reactions[0].name == "Red Heart"
        assert result.reactions[1].reaction_id == "74"
        assert result.reactions[1].emoji_char == "🇮🇷"
        assert result.reactions[1].name == "Iran"

        await client.stop()

    asyncio.run(scenario())


def test_get_contacts_updates_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getContactsUpdates"
            assert decrypted_request["input"] == {
                "state": 1774239888,
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "users": [],
                        "deleted_users": [],
                        "new_state": 1774284426,
                        "status": "OK",
                        "timestamp": "1774284486",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_contacts_updates(1774239888)

        assert result.users == []
        assert result.deleted_users == []
        assert result.new_state == 1774284426
        assert result.status == "OK"
        assert result.timestamp == "1774284486"

        await client.stop()

    asyncio.run(scenario())


def test_delete_chat_history_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "deleteChatHistory"
            assert decrypted_request["input"] == {
                "object_guid": "u0Crz5308d9ca919827a835fac44dbae",
                "last_message_id": "1557045568911832",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "chat_update": {
                            "object_guid": "u0Crz5308d9ca919827a835fac44dbae",
                            "action": "Edit",
                            "chat": {
                                "count_unseen": 0,
                                "last_message": {
                                    "message_id": "0",
                                    "type": "NotMessage",
                                    "text": "تاریخچه پاک شد.",
                                },
                                "last_message_id": "0",
                                "last_deleted_mid": "1557045568911832",
                            },
                            "updated_parameters": [
                                "last_message",
                                "last_message_id",
                                "count_unseen",
                                "last_deleted_mid",
                            ],
                            "timestamp": "1774236945",
                            "type": "User",
                        }
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.delete_chat_history(
            "u0Crz5308d9ca919827a835fac44dbae",
            last_message_id="1557045568911832",
        )

        assert result.chat_update is not None
        assert result.chat_update.object_guid == "u0Crz5308d9ca919827a835fac44dbae"
        assert result.chat_update.chat is not None
        assert result.chat_update.chat.last_deleted_mid == "1557045568911832"
        assert result.chat_update.chat.last_message is not None
        assert result.chat_update.chat.last_message.text == "تاریخچه پاک شد."

        await client.stop()

    asyncio.run(scenario())


def test_delete_chat_history_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.delete_chat_history(
            peer=Message(object_guid="u0Crz5308d9ca919827a835fac44dbae"),
            last_message_id="1557045568911832",
        )

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], DeleteChatHistory)
        assert calls[0].object_guid == "u0Crz5308d9ca919827a835fac44dbae"
        assert calls[0].last_message_id == "1557045568911832"

    asyncio.run(scenario())


def test_send_chat_activity_returns_empty_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "sendChatActivity"
            assert decrypted_request["input"] == {
                "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "activity": "Typing",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {},
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.send_chat_activity(
            "c0DSKDg07c609895e68c2ac53ba69faa",
            activity="Typing",
        )

        assert result is not None
        assert result.__dict__ == {"_client": client}

        await client.stop()

    asyncio.run(scenario())


def test_send_chat_activity_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.send_chat_activity(
            peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"),
            activity="Typing",
        )

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], SendChatActivity)
        assert calls[0].object_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert calls[0].activity == "Typing"

    asyncio.run(scenario())


def test_send_typing_uses_send_chat_activity(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_send_chat_activity(self, object_guid=None, activity="Typing", *, peer=None):
            calls.append(
                {
                    "object_guid": object_guid,
                    "activity": activity,
                    "peer": peer,
                }
            )
            return "ok"

        monkeypatch.setattr(type(client), "send_chat_activity", fake_send_chat_activity)

        result = await client.send_typing("c0DSKDg07c609895e68c2ac53ba69faa")

        assert result == "ok"
        assert calls == [
            {
                "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "activity": "Typing",
                "peer": None,
            }
        ]

    asyncio.run(scenario())


def test_send_chat_activity_rejects_bot_sessions():
    async def scenario():
        client = Client("test", token="bot-token")
        try:
            await client.send_chat_activity("c0", activity="Typing")
        except RuntimeError as exc:
            assert str(exc) == "send_chat_activity() is only available for authenticated user sessions"
        else:
            raise AssertionError("Expected RuntimeError")

    asyncio.run(scenario())


def test_add_group_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "addGroup"
            assert decrypted_request["input"] == {
                "title": "تست",
                "member_guids": ["b0NMS0012c504de75ddb83f3bbc00f21"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Visible",
                            "event_messages": True,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": False,
                        },
                        "chat_update": {
                            "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "action": "New",
                            "chat": {
                                "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                                "count_unseen": 0,
                                "last_message": {
                                    "message_id": "0",
                                    "type": "NotMessage",
                                    "text": "گروه جدید ایجاد شد.",
                                },
                                "last_message_id": "0",
                                "last_deleted_mid": "0",
                            },
                            "updated_parameters": [],
                            "timestamp": "1774237116",
                            "type": "Group",
                        },
                        "message_update": {
                            "message_id": "1571692526621380",
                            "action": "New",
                            "message": {
                                "message_id": "1571692526621380",
                                "text": "گروه تست ایجاد شد.",
                                "time": "1774237116",
                                "type": "Event",
                                "event_data": {
                                    "type": "GroupCreated",
                                    "performer_object": {
                                        "type": "User",
                                        "object_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                    },
                                    "title": "تست",
                                },
                            },
                            "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "type": "Group",
                        },
                        "timestamp": "1774237116",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.add_group("تست", member_guids=["b0NMS0012c504de75ddb83f3bbc00f21"])

        assert result.group is not None
        assert result.group.group_guid == "g0HJRjv02cfa6363ca148b8d3351ca6d"
        assert result.group.chat_reaction_setting is not None
        assert result.group.chat_reaction_setting.reaction_type == "All"
        assert result.chat_update is not None
        assert result.chat_update.object_guid == "g0HJRjv02cfa6363ca148b8d3351ca6d"
        assert result.message_update is not None
        assert result.message_update.message is not None
        assert result.message_update.message.text == "گروه تست ایجاد شد."
        assert result.timestamp == "1774237116"

        await client.stop()

    asyncio.run(scenario())


def test_add_channel_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "addChannel"
            assert decrypted_request["input"] == {
                "title": "ll",
                "description": "توضیحات",
                "channel_type": "Private",
                "member_guids": ["u0Crz5308d9ca919827a835fac44dbae"],
                "thumbnail_file_id": "88602634217110",
                "main_file_id": "88602629903555",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "channel": {
                            "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "channel_title": "ll",
                            "avatar_thumbnail": {
                                "file_id": "88602634217110",
                                "mime": "jpg",
                                "dc_id": "846",
                                "access_hash_rec": "0998626527273395641776449175542026032307",
                            },
                            "count_members": 2,
                            "description": "توضیحات",
                            "is_deleted": False,
                            "is_verified": False,
                            "channel_type": "Private",
                            "sign_messages": False,
                            "chat_reaction_setting": {"reaction_type": "Disabled"},
                            "is_restricted_content": False,
                        },
                        "chat_update": {
                            "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "action": "New",
                            "chat": {
                                "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                                "access": [
                                    "ChangeInfo",
                                    "ViewMembers",
                                    "ViewAdmins",
                                    "PinMessages",
                                    "SendMessages",
                                    "EditAllMessages",
                                    "DeleteGlobalAllMessages",
                                    "AddMember",
                                    "SetAdmin",
                                    "SetJoinLink",
                                    "SuperAdmin",
                                    "RemoveObject",
                                    "ViewInfo",
                                    "ViewMessages",
                                ],
                                "count_unseen": 1,
                                "is_mute": False,
                                "is_pinned": False,
                                "time_string": "177424007100001571706695825913",
                                "last_message": {
                                    "message_id": "1571706695825913",
                                    "type": "Other",
                                    "text": "کانال ll ایجاد شد.",
                                    "is_mine": False,
                                },
                                "last_seen_my_mid": "0",
                                "last_seen_peer_mid": "0",
                                "status": "Active",
                                "time": 1774240071,
                                "abs_object": {
                                    "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                                    "type": "Channel",
                                    "title": "ll",
                                    "avatar_thumbnail": {
                                        "file_id": "88602634217110",
                                        "mime": "jpg",
                                        "dc_id": "846",
                                        "access_hash_rec": "0998626527273395641776449175542026032307",
                                    },
                                    "is_verified": False,
                                    "is_deleted": False,
                                },
                                "is_blocked": False,
                                "last_message_id": "1571706695825913",
                                "last_deleted_mid": "0",
                                "show_ask_spam": False,
                                "auto_delete": "Off",
                            },
                            "updated_parameters": [],
                            "timestamp": "1774240071",
                            "type": "Channel",
                        },
                        "message_update": {
                            "message_id": "1571706695825913",
                            "action": "New",
                            "message": {
                                "message_id": "1571706695825913",
                                "text": "کانال ll ایجاد شد.",
                                "time": "1774240071",
                                "is_edited": False,
                                "type": "Event",
                                "event_data": {
                                    "type": "ChannelCreated",
                                    "title": "ll",
                                },
                                "allow_transcription": False,
                            },
                            "updated_parameters": [],
                            "timestamp": "1774240071",
                            "prev_message_id": "0",
                            "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "type": "Channel",
                            "state": "1774240011",
                            "is_scheduled": False,
                        },
                        "timestamp": "1774240071",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.add_channel(
            "ll",
            description="توضیحات",
            channel_type="Private",
            member_guids=["u0Crz5308d9ca919827a835fac44dbae"],
            thumbnail_file_id="88602634217110",
            main_file_id="88602629903555",
        )

        assert result.channel is not None
        assert result.channel.channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert result.channel.channel_title == "ll"
        assert result.channel.description == "توضیحات"
        assert result.channel.channel_type == "Private"
        assert result.channel.avatar_thumbnail is not None
        assert result.channel.avatar_thumbnail.file_id == "88602634217110"
        assert result.channel.chat_reaction_setting is not None
        assert result.channel.chat_reaction_setting.reaction_type == "Disabled"
        assert result.chat_update is not None
        assert result.chat_update.object_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert result.message_update is not None
        assert result.message_update.message is not None
        assert result.message_update.message.text == "کانال ll ایجاد شد."
        assert result.timestamp == "1774240071"

        await client.stop()

    asyncio.run(scenario())


def test_add_channel_members_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "addChannelMembers"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "member_guids": ["u0Crz5308d9ca919827a835fac44dbae"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "added_in_chat_members": [
                            {
                                "member_type": "User",
                                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                                "first_name": "Ehsan Davari",
                                "last_name": "",
                                "is_verified": False,
                                "is_deleted": False,
                                "last_online": 1774211400,
                                "join_type": "Member",
                                "username": "ehsndvr",
                                "online_time": {
                                    "type": "Approximate",
                                    "approximate_period": "Recently",
                                },
                            }
                        ],
                        "timestamp": "1774284632",
                        "channel": {
                            "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "channel_title": "ll",
                            "avatar_thumbnail": {
                                "file_id": "88602634217110",
                                "mime": "jpg",
                                "dc_id": "846",
                                "access_hash_rec": "0998626527273395641776449175542026032307",
                            },
                            "count_members": 2,
                            "description": "توضیحاتc",
                            "is_deleted": False,
                            "is_verified": False,
                            "channel_type": "Private",
                            "sign_messages": False,
                            "chat_reaction_setting": {
                                "reaction_type": "Selected",
                                "selected_reactions": ["3", "2"],
                            },
                            "is_restricted_content": False,
                        },
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.add_channel_members(
            "c0DSKDg07c609895e68c2ac53ba69faa",
            member_guids=["u0Crz5308d9ca919827a835fac44dbae"],
        )

        assert len(result.added_in_chat_members) == 1
        assert result.added_in_chat_members[0].member_guid == "u0Crz5308d9ca919827a835fac44dbae"
        assert result.added_in_chat_members[0].join_type == "Member"
        assert result.channel is not None
        assert result.channel.channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert result.channel.avatar_thumbnail is not None
        assert result.channel.chat_reaction_setting is not None
        assert result.channel.chat_reaction_setting.selected_reactions == ["3", "2"]
        assert result.timestamp == "1774284632"

        await client.stop()

    asyncio.run(scenario())


def test_add_channel_members_accepts_peer_values(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.add_channel_members(
            peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"),
            member_guids=[Message(object_guid="u0Crz5308d9ca919827a835fac44dbae")],
        )

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], AddChannelMembers)
        assert calls[0].channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert calls[0].member_guids == ["u0Crz5308d9ca919827a835fac44dbae"]

    asyncio.run(scenario())


def test_get_channel_link_returns_empty_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getChannelLink"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {},
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_channel_link("c0DSKDg07c609895e68c2ac53ba69faa")

        assert result is not None
        assert result.__dict__ == {"_client": client}

        await client.stop()

    asyncio.run(scenario())


def test_get_channel_link_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.get_channel_link(peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"))

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], GetChannelLink)
        assert calls[0].channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"

    asyncio.run(scenario())


def test_get_channel_info_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getChannelInfo"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "channel": {
                            "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "channel_title": "ll",
                            "avatar_thumbnail": {
                                "file_id": "88602634217110",
                                "mime": "jpg",
                                "dc_id": "846",
                                "access_hash_rec": "0998626527273395641776449175542026032307",
                            },
                            "count_members": 2,
                            "description": "توضیحات",
                            "is_deleted": False,
                            "is_verified": False,
                            "channel_type": "Private",
                            "sign_messages": False,
                            "chat_reaction_setting": {"reaction_type": "Disabled"},
                            "is_restricted_content": False,
                        },
                        "chat": {
                            "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "access": [
                                "ChangeInfo",
                                "ViewMembers",
                                "ViewAdmins",
                                "PinMessages",
                                "SendMessages",
                                "EditAllMessages",
                                "DeleteGlobalAllMessages",
                                "AddMember",
                                "SetAdmin",
                                "SetJoinLink",
                                "SuperAdmin",
                                "RemoveObject",
                                "ViewInfo",
                                "ViewMessages",
                            ],
                            "count_unseen": 1,
                            "is_mute": False,
                            "is_pinned": False,
                            "time_string": "177427561100001572408061444913",
                            "last_message": {
                                "message_id": "1572408061444913",
                                "type": "Text",
                                "text": "s",
                                "is_mine": False,
                            },
                            "last_seen_my_mid": "1571706695825913",
                            "last_seen_peer_mid": "0",
                            "status": "Active",
                            "time": 1774275611,
                            "abs_object": {
                                "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                                "type": "Channel",
                                "title": "ll",
                                "avatar_thumbnail": {
                                    "file_id": "88602634217110",
                                    "mime": "jpg",
                                    "dc_id": "846",
                                    "access_hash_rec": "0998626527273395641776449175542026032307",
                                },
                                "is_verified": False,
                                "is_deleted": False,
                            },
                            "is_blocked": False,
                            "last_message_id": "1572408061444913",
                            "last_deleted_mid": "0",
                            "show_ask_spam": False,
                            "auto_delete": "Off",
                        },
                        "timestamp": "1774275752",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_channel_info("c0DSKDg07c609895e68c2ac53ba69faa")

        assert result.channel is not None
        assert result.channel.channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert result.channel.channel_title == "ll"
        assert result.channel.avatar_thumbnail is not None
        assert result.channel.avatar_thumbnail.file_id == "88602634217110"
        assert result.chat is not None
        assert result.chat.object_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert result.chat.last_message is not None
        assert result.chat.last_message.object_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert result.chat.abs_object is not None
        assert result.chat.abs_object.avatar_thumbnail is not None
        assert result.chat.abs_object.avatar_thumbnail.file_id == "88602634217110"
        assert result.timestamp == "1774275752"

        await client.stop()

    asyncio.run(scenario())


def test_get_channel_info_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.get_channel_info(peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"))

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], GetChannelInfo)
        assert calls[0].channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"

    asyncio.run(scenario())


def test_get_channel_info_avatar_thumbnail_downloads(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        payload = {
            "channel": {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "avatar_thumbnail": {
                    "file_id": "88602634217110",
                    "mime": "jpg",
                    "dc_id": "846",
                    "access_hash_rec": "0998626527273395641776449175542026032307",
                },
            },
            "chat": {
                "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "abs_object": {
                    "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                    "type": "Channel",
                    "avatar_thumbnail": {
                        "file_id": "88602634217110",
                        "mime": "jpg",
                        "dc_id": "846",
                        "access_hash_rec": "0998626527273395641776449175542026032307",
                    },
                },
            },
        }
        result = client.raw.methods.GetChannelInfo(channel_guid="c0").parse_response(client, payload)
        calls = []

        async def fake_download_file(self, file, path=None, in_memory=False, file_name=None, progress=None, progress_args=()):
            calls.append(
                {
                    "file_id": getattr(file, "file_id", None),
                    "path": path,
                    "in_memory": in_memory,
                    "file_name": file_name,
                }
            )
            return b"ok"

        monkeypatch.setattr(Client, "download_file", fake_download_file)

        content1 = await result.channel.avatar_thumbnail.download(in_memory=True, file_name="channel.jpg")  # type: ignore[union-attr]
        content2 = await result.chat.abs_object.avatar_thumbnail.download(in_memory=True, file_name="abs.jpg")  # type: ignore[union-attr]

        assert content1 == b"ok"
        assert content2 == b"ok"
        assert calls == [
            {
                "file_id": "88602634217110",
                "path": None,
                "in_memory": True,
                "file_name": "channel.jpg",
            },
            {
                "file_id": "88602634217110",
                "path": None,
                "in_memory": True,
                "file_name": "abs.jpg",
            },
        ]

    asyncio.run(scenario())


def test_get_channel_all_members_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getChannelAllMembers"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "in_chat_members": [
                            {
                                "member_type": "User",
                                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                                "first_name": "Ehsan Davari",
                                "last_name": "",
                                "is_verified": False,
                                "is_deleted": False,
                                "last_online": 1774211400,
                                "join_type": "Member",
                                "username": "ehsndvr",
                                "online_time": {
                                    "type": "Approximate",
                                    "approximate_period": "Recently",
                                },
                            },
                            {
                                "member_type": "User",
                                "member_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                "first_name": "King",
                                "is_verified": False,
                                "is_deleted": False,
                                "last_online": 1774275597,
                                "join_type": "Creator",
                                "username": "Amie6609",
                                "online_time": {
                                    "type": "Exact",
                                    "exact_time": 1774275597,
                                },
                            },
                        ],
                        "has_continue": False,
                        "timestamp": "1774275753",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_channel_all_members("c0DSKDg07c609895e68c2ac53ba69faa")

        assert len(result.in_chat_members) == 2
        assert result.in_chat_members[0].member_guid == "u0Crz5308d9ca919827a835fac44dbae"
        assert result.in_chat_members[0].first_name == "Ehsan Davari"
        assert result.in_chat_members[0].join_type == "Member"
        assert result.in_chat_members[0].online_time is not None
        assert result.in_chat_members[0].online_time.approximate_period == "Recently"
        assert result.in_chat_members[1].member_guid == "u0DiqTP0d4d36e090fb7060d540a33c7"
        assert result.in_chat_members[1].join_type == "Creator"
        assert result.in_chat_members[1].online_time is not None
        assert result.in_chat_members[1].online_time.exact_time == 1774275597
        assert result.has_continue is False
        assert result.timestamp == "1774275753"

        await client.stop()

    asyncio.run(scenario())


def test_get_channel_all_members_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.get_channel_all_members(peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"))

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], GetChannelAllMembers)
        assert calls[0].channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"

    asyncio.run(scenario())


def test_edit_channel_info_updates_title_and_description(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "editChannelInfo"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "title": "ll",
                "description": "توضیحاتc",
                "updated_parameters": ["title", "description"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "channel": {
                            "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "channel_title": "ll",
                            "avatar_thumbnail": {
                                "file_id": "88602634217110",
                                "mime": "jpg",
                                "dc_id": "846",
                                "access_hash_rec": "0998626527273395641776449175542026032307",
                            },
                            "count_members": 2,
                            "description": "توضیحاتc",
                            "is_deleted": False,
                            "is_verified": False,
                            "channel_type": "Private",
                            "sign_messages": False,
                            "chat_reaction_setting": {
                                "reaction_type": "Selected",
                                "selected_reactions": ["3", "2"],
                            },
                            "is_restricted_content": False,
                        },
                        "chat_update": {
                            "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                            "action": "Edit",
                            "chat": {
                                "abs_object": {
                                    "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                                    "type": "Channel",
                                    "title": "ll",
                                    "avatar_thumbnail": {
                                        "file_id": "88602634217110",
                                        "mime": "jpg",
                                        "dc_id": "846",
                                        "access_hash_rec": "0998626527273395641776449175542026032307",
                                    },
                                    "is_verified": False,
                                    "is_deleted": False,
                                }
                            },
                            "updated_parameters": ["abs_object"],
                            "timestamp": "1774284150",
                            "type": "Channel",
                        },
                        "timestamp": "1774284150",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.edit_channel_info(
            "c0DSKDg07c609895e68c2ac53ba69faa",
            title="ll",
            description="توضیحاتc",
        )

        assert result.channel is not None
        assert result.channel.channel_title == "ll"
        assert result.channel.description == "توضیحاتc"
        assert result.channel.chat_reaction_setting is not None
        assert result.channel.chat_reaction_setting.reaction_type == "Selected"
        assert result.channel.chat_reaction_setting.selected_reactions == ["3", "2"]
        assert result.chat_update is not None
        assert result.chat_update.object_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert result.chat_update.chat is not None
        assert result.chat_update.chat.abs_object is not None
        assert result.chat_update.chat.abs_object.avatar_thumbnail is not None
        assert result.timestamp == "1774284150"

        await client.stop()

    asyncio.run(scenario())


def test_edit_channel_info_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.edit_channel_info(
            peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"),
            title="ll",
            description="توضیحاتc",
        )

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], EditChannelInfo)
        assert calls[0].channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"
        assert calls[0].updated_parameters == ["title", "description"]

    asyncio.run(scenario())


def test_edit_channel_info_requires_at_least_one_supported_field():
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)

        try:
            await client.edit_channel_info("c0DSKDg07c609895e68c2ac53ba69faa")
        except ValueError as exc:
            assert str(exc) == "At least one supported channel field must be provided"
        else:
            raise AssertionError("Expected ValueError")

    asyncio.run(scenario())


def test_get_channel_admin_members_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getChannelAdminMembers"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "in_chat_members": [
                            {
                                "member_type": "User",
                                "member_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                "first_name": "King",
                                "is_verified": False,
                                "is_deleted": False,
                                "last_online": 1774284227,
                                "join_type": "Creator",
                                "username": "Amie6609",
                                "online_time": {
                                    "type": "Exact",
                                    "exact_time": 1774284227,
                                },
                            }
                        ],
                        "next_start_id": "69c0c1472b7c9ba33d9d6f7b",
                        "has_continue": False,
                        "timestamp": "1774284227",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_channel_admin_members("c0DSKDg07c609895e68c2ac53ba69faa")

        assert len(result.in_chat_members) == 1
        assert result.in_chat_members[0].member_guid == "u0DiqTP0d4d36e090fb7060d540a33c7"
        assert result.in_chat_members[0].join_type == "Creator"
        assert result.in_chat_members[0].online_time is not None
        assert result.in_chat_members[0].online_time.exact_time == 1774284227
        assert result.next_start_id == "69c0c1472b7c9ba33d9d6f7b"
        assert result.has_continue is False
        assert result.timestamp == "1774284227"

        await client.stop()

    asyncio.run(scenario())


def test_get_channel_admin_members_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.get_channel_admin_members(peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"))

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], GetChannelAdminMembers)
        assert calls[0].channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"

    asyncio.run(scenario())


def test_set_channel_admin_accepts_enum_access_list_and_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "setChannelAdmin"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                "action": "SetAdmin",
                "access_list": [
                    "ChangeInfo",
                    "ViewMembers",
                    "ViewAdmins",
                    "PinMessages",
                    "SendMessages",
                    "EditAllMessages",
                    "DeleteGlobalAllMessages",
                    "AddMember",
                    "SetJoinLink",
                    "SetAdmin",
                ],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "in_chat_member": {
                            "member_type": "User",
                            "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                            "first_name": "Ehsan Davari",
                            "last_name": "",
                            "is_verified": False,
                            "is_deleted": False,
                            "promoted_by_object_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                            "promoted_by_object_type": "User",
                            "join_type": "Admin",
                            "username": "ehsndvr",
                            "online_time": {
                                "type": "Approximate",
                                "approximate_period": "Recently",
                            },
                        },
                        "timestamp": "1774284282",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_channel_admin(
            "c0DSKDg07c609895e68c2ac53ba69faa",
            "u0Crz5308d9ca919827a835fac44dbae",
            [
                "ChangeInfo",
                "ViewMembers",
                "ViewAdmins",
                GroupAdminAccess.PIN_MESSAGES,
                "SendMessages",
                "EditAllMessages",
                GroupAdminAccess.DELETE_GLOBAL_ALL_MESSAGES,
                "AddMember",
                GroupAdminAccess.SET_JOIN_LINK,
                GroupAdminAccess.SET_ADMIN,
            ],
        )

        assert result.timestamp == "1774284282"
        assert result.in_chat_member is not None
        assert result.in_chat_member.member_guid == "u0Crz5308d9ca919827a835fac44dbae"
        assert result.in_chat_member.join_type == "Admin"
        assert result.in_chat_member.promoted_by_object_guid == "u0DiqTP0d4d36e090fb7060d540a33c7"
        assert result.in_chat_member.online_time is not None
        assert result.in_chat_member.online_time.approximate_period == "Recently"

        await client.stop()

    asyncio.run(scenario())


def test_update_channel_admin_access_accepts_string_access_list(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "setChannelAdmin"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                "action": "SetAdmin",
                "access_list": [
                    "ChangeInfo",
                    "ViewMembers",
                    "ViewAdmins",
                    "PinMessages",
                    "SendMessages",
                    "EditAllMessages",
                    "DeleteGlobalAllMessages",
                    "AddMember",
                    "SetJoinLink",
                    "SetAdmin",
                ],
            }
            return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.update_channel_admin_access(
            "c0DSKDg07c609895e68c2ac53ba69faa",
            "u0Crz5308d9ca919827a835fac44dbae",
            [
                "ChangeInfo",
                "ViewMembers",
                "ViewAdmins",
                "PinMessages",
                "SendMessages",
                "EditAllMessages",
                "DeleteGlobalAllMessages",
                "AddMember",
                "SetJoinLink",
                "SetAdmin",
            ],
        )

        assert result.in_chat_member is None

        await client.stop()

    asyncio.run(scenario())


def test_unset_channel_admin_uses_unset_admin_action(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "setChannelAdmin"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                "action": "UnsetAdmin",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "in_chat_member": {
                            "member_type": "User",
                            "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                            "first_name": "Ehsan Davari",
                            "last_name": "",
                            "is_verified": False,
                            "is_deleted": False,
                            "join_type": "Member",
                            "username": "ehsndvr",
                            "online_time": {
                                "type": "Approximate",
                                "approximate_period": "Recently",
                            },
                        },
                        "timestamp": "1774284708",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.unset_channel_admin(
            "c0DSKDg07c609895e68c2ac53ba69faa",
            "u0Crz5308d9ca919827a835fac44dbae",
        )

        assert result.in_chat_member is not None
        assert result.in_chat_member.member_guid == "u0Crz5308d9ca919827a835fac44dbae"
        assert result.in_chat_member.join_type == "Member"
        assert result.in_chat_member.online_time is not None
        assert result.in_chat_member.online_time.approximate_period == "Recently"
        assert result.timestamp == "1774284708"

        await client.stop()

    asyncio.run(scenario())


def test_get_banned_channel_members_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getBannedChannelMembers"
            assert decrypted_request["input"] == {
                "channel_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "in_chat_members": [],
                        "has_continue": False,
                        "timestamp": "1774284380",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_banned_channel_members("c0DSKDg07c609895e68c2ac53ba69faa")

        assert result.in_chat_members == []
        assert result.has_continue is False
        assert result.timestamp == "1774284380"

        await client.stop()

    asyncio.run(scenario())


def test_get_banned_channel_members_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.get_banned_channel_members(peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"))

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], GetBannedChannelMembers)
        assert calls[0].channel_guid == "c0DSKDg07c609895e68c2ac53ba69faa"

    asyncio.run(scenario())


def test_get_profile_link_items_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getProfileLinkItems"
            assert decrypted_request["input"] == {
                "object_guid": "c0DSKDg07c609895e68c2ac53ba69faa",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "link_items": [
                            {
                                "title": "داشبورد کسب درآمد",
                                "link": {
                                    "type": "inlineopenurl",
                                    "inline_open_url_data": {
                                        "title": "داشبورد کسب درآمد",
                                        "url": "https://income-dash.rubika.ir/default.aspx?cid=c0DSKDg07c609895e68c2ac53ba69faa&pw=15870d89de8792a6867ca3af0d24e9c0",
                                    },
                                },
                            }
                        ],
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_profile_link_items("c0DSKDg07c609895e68c2ac53ba69faa")

        assert len(result.link_items) == 1
        assert result.link_items[0].title == "داشبورد کسب درآمد"
        assert result.link_items[0].link is not None
        assert result.link_items[0].link.type == "inlineopenurl"
        assert result.link_items[0].link.inline_open_url_data is not None
        assert result.link_items[0].link.inline_open_url_data.title == "داشبورد کسب درآمد"
        assert result.link_items[0].link.inline_open_url_data.url == "https://income-dash.rubika.ir/default.aspx?cid=c0DSKDg07c609895e68c2ac53ba69faa&pw=15870d89de8792a6867ca3af0d24e9c0"

        await client.stop()

    asyncio.run(scenario())


def test_get_profile_link_items_accepts_peer_objects(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.get_profile_link_items(peer=Message(object_guid="c0DSKDg07c609895e68c2ac53ba69faa"))

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], GetProfileLinkItems)
        assert calls[0].object_guid == "c0DSKDg07c609895e68c2ac53ba69faa"

    asyncio.run(scenario())


def test_search_global_objects_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("bxmalqzstnqidtoikvoxjwcuhxrmescj")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "searchGlobalObjects"
            assert decrypted_request["input"] == {
                "search_text": "Ehsan",
                "filter_types": ["Bot"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "objects": [
                            {
                                "object_guid": "b0NMS0012c504de75ddb83f3bbc00f21",
                                "type": "Bot",
                                "title": "Ehsan",
                                "is_verified": False,
                                "is_deleted": False,
                                "username": "ehsan007_fun_bot",
                                "track_id": "searchBackend*2",
                            },
                            {
                                "object_guid": "c0BwPAt02388b73779f96b2cbc483f64",
                                "type": "Channel",
                                "title": "احسان باکستر | Ehsan Boxter",
                                "avatar_thumbnail": {
                                    "file_id": "38362377284747",
                                    "mime": "jpg",
                                    "dc_id": "865",
                                    "access_hash_rec": "2979188977369059586422992546152024040402",
                                },
                                "is_verified": True,
                                "is_deleted": False,
                                "count_members": 9175,
                                "username": "ehsanboxter",
                                "track_id": "{'l': 'messenger', 'svc': 'search_channel', 'm': 'search', 's': 'Ehsan', 'r': 0, 'ref': '26839627'}",
                            },
                        ],
                        "has_continue": False,
                        "timestamp": "1774284489",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.search_global_objects("Ehsan", filter_types=["Bot"])

        assert len(result.objects) == 2
        assert result.objects[0].object_guid == "b0NMS0012c504de75ddb83f3bbc00f21"
        assert result.objects[0].type == "Bot"
        assert result.objects[0].title == "Ehsan"
        assert result.objects[1].type == "Channel"
        assert result.objects[1].avatar_thumbnail is not None
        assert result.objects[1].avatar_thumbnail.file_id == "38362377284747"
        assert result.objects[1].count_members == 9175
        assert result.has_continue is False
        assert result.timestamp == "1774284489"

        await client.stop()

    asyncio.run(scenario())


def test_search_global_objects_avatar_thumbnail_downloads(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        payload = {
            "objects": [
                {
                    "object_guid": "c0BwPAt02388b73779f96b2cbc483f64",
                    "type": "Channel",
                    "title": "احسان باکستر | Ehsan Boxter",
                    "avatar_thumbnail": {
                        "file_id": "38362377284747",
                        "mime": "jpg",
                        "dc_id": "865",
                        "access_hash_rec": "2979188977369059586422992546152024040402",
                    },
                    "is_verified": True,
                    "is_deleted": False,
                    "count_members": 9175,
                    "username": "ehsanboxter",
                    "track_id": "searchBackend*channel",
                }
            ],
            "has_continue": False,
            "timestamp": "1774284489",
        }
        result = client.raw.methods.SearchGlobalObjects(search_text="Ehsan", filter_types=["Bot"]).parse_response(client, payload)
        calls = []

        async def fake_download_file(self, file, path=None, in_memory=False, file_name=None, progress=None, progress_args=()):
            calls.append(
                {
                    "file_id": getattr(file, "file_id", None),
                    "in_memory": in_memory,
                    "file_name": file_name,
                }
            )
            return b"ok"

        monkeypatch.setattr(Client, "download_file", fake_download_file)

        content = await result.objects[0].avatar_thumbnail.download(in_memory=True, file_name="search-avatar.jpg")  # type: ignore[union-attr]

        assert content == b"ok"
        assert calls == [
            {
                "file_id": "38362377284747",
                "in_memory": True,
                "file_name": "search-avatar.jpg",
            }
        ]

    asyncio.run(scenario())


def test_add_group_members_accepts_peer_values(monkeypatch):
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        calls = []

        async def fake_invoke(method):
            calls.append(method)
            return "ok"

        client.invoke = fake_invoke  # type: ignore[method-assign]

        result = await client.add_group_members(
            peer=Message(object_guid="g0group"),
            member_guids=[Message(object_guid="u0member"), "b0botmember"],
        )

        assert result == "ok"
        assert len(calls) == 1
        assert isinstance(calls[0], AddGroupMembers)
        assert calls[0].group_guid == "g0group"
        assert calls[0].member_guids == ["u0member", "b0botmember"]

    asyncio.run(scenario())


def test_upload_group_avatar_uploads_then_invokes_rpc(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        temp_path = Path.cwd() / f"_group_avatar_{uuid.uuid4().hex}.jpg"
        temp_path.write_bytes(b"JPEGDATA")

        async def upload_file(self, *, auth, descriptor, path, progress=None, progress_args=()):
            assert auth == "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
            assert Path(path) == temp_path
            return client_module.UploadDescriptor(
                id=descriptor.id,
                dc_id=descriptor.dc_id,
                access_hash_send=descriptor.access_hash_send,
                access_hash_rec="group-avatar-rec",
                upload_url=descriptor.upload_url,
            )

        monkeypatch.setattr(client_module.UploadTransport, "upload_file", upload_file)

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            method = decrypted_request["method"]

            if method == "requestSendFile":
                assert decrypted_request["input"] == {
                    "file_name": temp_path.name,
                    "size": temp_path.stat().st_size,
                    "mime": "jpg",
                }
                return encrypt_response(
                    {
                        "status": "OK",
                        "status_det": "OK",
                        "data": {
                            "id": "88001038289475",
                            "dc_id": "410",
                            "access_hash_send": "group-avatar-send",
                            "upload_url": "https://upmessenger410.iranlms.ir/UploadFile.ashx",
                        },
                    },
                    auth,
                )

            if method == "uploadNewGroupAvatar":
                assert decrypted_request["input"] == {
                    "group_guid": "g0group",
                    "file_id": "88001038289475",
                    "dc_id": "410",
                    "access_hash_rec": "group-avatar-rec",
                }
                return encrypt_response({"status": "OK", "status_det": "OK", "data": {"status": "OK"}}, auth)

            raise AssertionError(f"Unexpected method: {method}")

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.upload_group_avatar("g0group", temp_path)

        assert result.status == "OK"

        temp_path.unlink(missing_ok=True)
        await client.stop()

    asyncio.run(scenario())


def test_get_group_info_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getGroupInfo"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Visible",
                            "event_messages": True,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": False,
                        },
                        "chat": {
                            "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "access": [
                                "ChangeInfo",
                                "PinMessages",
                                "DeleteGlobalAllMessages",
                            ],
                            "count_unseen": 1,
                            "is_mute": False,
                            "is_pinned": False,
                            "time_string": "177423711600001571692526621380",
                            "last_message": {
                                "message_id": "1571692526621380",
                                "type": "Other",
                                "text": "گروه تست ایجاد شد.",
                                "is_mine": False,
                            },
                            "last_seen_my_mid": "0",
                            "last_seen_peer_mid": "0",
                            "status": "Active",
                            "time": 1774237116,
                            "abs_object": {
                                "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                                "type": "Group",
                                "title": "تست",
                                "is_verified": False,
                                "is_deleted": False,
                            },
                            "is_blocked": False,
                            "last_message_id": "1571692526621380",
                            "last_deleted_mid": "0",
                            "slow_mode_duration": 0,
                            "show_ask_spam": False,
                            "auto_delete": "Off",
                        },
                        "timestamp": "1774237116",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_group_info("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert result.group is not None
        assert result.group.group_guid == "g0HJRjv02cfa6363ca148b8d3351ca6d"
        assert result.group.group_title == "تست"
        assert result.group.chat_reaction_setting is not None
        assert result.group.chat_reaction_setting.reaction_type == "All"
        assert result.chat is not None
        assert result.chat.object_guid == "g0HJRjv02cfa6363ca148b8d3351ca6d"
        assert result.chat.last_message is not None
        assert result.chat.last_message.text == "گروه تست ایجاد شد."
        assert result.chat.last_message.object_guid == "g0HJRjv02cfa6363ca148b8d3351ca6d"
        assert result.timestamp == "1774237116"

        await client.stop()

    asyncio.run(scenario())


def test_get_group_all_members_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getGroupAllMembers"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "in_chat_members": [
                            {
                                "member_type": "Bot",
                                "member_guid": "b0NMS0012c504de75ddb83f3bbc00f21",
                                "title": "Ehsan",
                                "is_verified": False,
                                "is_deleted": False,
                                "join_type": "Member",
                                "username": "ehsan007_fun_bot",
                            },
                            {
                                "member_type": "User",
                                "member_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                "first_name": "King",
                                "is_verified": False,
                                "is_deleted": False,
                                "last_online": 1774237744,
                                "join_type": "Creator",
                                "username": "Amie6609",
                                "online_time": {
                                    "type": "Exact",
                                    "exact_time": 1774237744,
                                },
                            },
                        ],
                        "has_continue": False,
                        "timestamp": "1774237744",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_group_all_members("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert len(result.in_chat_members) == 2
        assert result.in_chat_members[0].member_type == "Bot"
        assert result.in_chat_members[0].title == "Ehsan"
        assert result.in_chat_members[0].username == "ehsan007_fun_bot"
        assert result.in_chat_members[1].member_type == "User"
        assert result.in_chat_members[1].first_name == "King"
        assert result.in_chat_members[1].join_type == "Creator"
        assert result.in_chat_members[1].online_time is not None
        assert result.in_chat_members[1].online_time.exact_time == 1774237744
        assert result.has_continue is False
        assert result.timestamp == "1774237744"

        await client.stop()

    asyncio.run(scenario())


def test_get_group_default_access_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getGroupDefaultAccess"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "access_list": [
                            "ViewMembers",
                            "ViewAdmins",
                            "SendMessages",
                        ]
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_group_default_access("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert result.access_list == ["ViewMembers", "ViewAdmins", "SendMessages"]

        await client.stop()

    asyncio.run(scenario())


def test_get_pending_object_owner_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getPendingObjectOwner"
            assert decrypted_request["input"] == {
                "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "exist_pending_owner": False,
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_pending_object_owner("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert result.exist_pending_owner is False

        await client.stop()

    asyncio.run(scenario())


def test_get_group_link_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getGroupLink"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "join_link": "https://rubika.ir/joing/JJACJHBD0WFGDWEZRHFHVQDNSLDCUTEU",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_group_link("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert result.join_link == "https://rubika.ir/joing/JJACJHBD0WFGDWEZRHFHVQDNSLDCUTEU"

        await client.stop()

    asyncio.run(scenario())


def test_get_join_links_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "getJoinLinks"
            assert decrypted_request["input"] == {
                "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "join_links": [],
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_join_links("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert result.join_links == []

        await client.stop()

    asyncio.run(scenario())


def test_create_join_link_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "createJoinLink"
            assert decrypted_request["input"] == {
                "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "title": "tt",
                "request_needed": False,
                "expire_time": 86400,
                "usage_limit": 10,
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "join_link": {
                            "object_guid": {
                                "type": "Group",
                                "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            },
                            "join_link": "https://rubika.ir/joing/+JJACJHBD0ITDCAGNMHWBIUSXAXLMSZNJ",
                            "creator_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                            "create_time": 1774238631,
                            "request_pending_count": 0,
                            "request_needed": False,
                            "usage_limit": 10,
                            "title": "tt",
                            "expire_time": 86400,
                            "expire_at": 1774325031,
                        }
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.create_join_link(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            title="tt",
            request_needed=False,
            expire_time=86400,
            usage_limit=10,
        )

        assert result.join_link is not None
        assert result.join_link.object_guid is not None
        assert result.join_link.object_guid.type == "Group"
        assert result.join_link.object_guid.object_guid == "g0HJRjv02cfa6363ca148b8d3351ca6d"
        assert result.join_link.join_link == "https://rubika.ir/joing/+JJACJHBD0ITDCAGNMHWBIUSXAXLMSZNJ"
        assert result.join_link.title == "tt"
        assert result.join_link.request_needed is False
        assert result.join_link.usage_limit == 10
        assert result.join_link.expire_time == 86400
        assert result.join_link.expire_at == 1774325031

        await client.stop()

    asyncio.run(scenario())


def test_edit_group_info_updates_event_messages(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "editGroupInfo"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "event_messages": True,
                "updated_parameters": ["event_messages"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Visible",
                            "event_messages": True,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": False,
                        },
                        "timestamp": "1774238754",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_event_messages("g0HJRjv02cfa6363ca148b8d3351ca6d", enabled=True)

        assert result.group is not None
        assert result.group.event_messages is True
        assert result.group.chat_history_for_new_members == "Visible"
        assert result.timestamp == "1774238754"

        await client.stop()

    asyncio.run(scenario())


def test_edit_group_info_updates_history_visibility(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "editGroupInfo"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "chat_history_for_new_members": "Hidden",
                "updated_parameters": ["chat_history_for_new_members"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Hidden",
                            "event_messages": False,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": False,
                        },
                        "timestamp": "1774238754",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_history_for_new_members(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            value="Hidden",
        )

        assert result.group is not None
        assert result.group.chat_history_for_new_members == "Hidden"
        assert result.group.event_messages is False
        assert result.timestamp == "1774238754"

        await client.stop()

    asyncio.run(scenario())


def test_edit_group_info_updates_slow_mode(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "editGroupInfo"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "slow_mode": 30,
                "updated_parameters": ["slow_mode"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 30,
                            "chat_history_for_new_members": "Hidden",
                            "event_messages": False,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": True,
                        },
                        "timestamp": "1774239075",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_slow_mode("g0HJRjv02cfa6363ca148b8d3351ca6d", seconds=30)

        assert result.group is not None
        assert result.group.slow_mode == 30
        assert result.timestamp == "1774239075"

        await client.stop()

    asyncio.run(scenario())


def test_edit_group_info_updates_reaction_setting_disabled(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "editGroupInfo"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "chat_reaction_setting": {"reaction_type": "Disabled"},
                "updated_parameters": ["chat_reaction_setting"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Hidden",
                            "event_messages": False,
                            "chat_reaction_setting": {"reaction_type": "Disabled"},
                            "is_restricted_content": True,
                        },
                        "timestamp": "1774239075",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_reactions_disabled("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert result.group is not None
        assert result.group.chat_reaction_setting is not None
        assert result.group.chat_reaction_setting.reaction_type == "Disabled"
        assert result.group.chat_reaction_setting.selected_reactions == []

        await client.stop()

    asyncio.run(scenario())


def test_edit_group_info_updates_reaction_setting_selected(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        selected = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
            "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
            "31", "32", "33", "34", "35", "36", "38", "40", "41", "42",
            "43", "44", "45", "46", "47", "48", "49", "50", "51", "52",
            "53", "54", "55", "56", "57", "58", "59", "60", "61", "62",
            "63", "64", "65", "74",
        ]

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "editGroupInfo"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "chat_reaction_setting": {
                    "reaction_type": "Selected",
                    "selected_reactions": selected,
                },
                "updated_parameters": ["chat_reaction_setting"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Hidden",
                            "event_messages": False,
                            "chat_reaction_setting": {
                                "reaction_type": "Selected",
                                "selected_reactions": selected,
                            },
                            "is_restricted_content": True,
                        },
                        "timestamp": "1774239075",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_reactions_selected(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            selected,
        )

        assert result.group is not None
        assert result.group.chat_reaction_setting is not None
        assert result.group.chat_reaction_setting.reaction_type == "Selected"
        assert result.group.chat_reaction_setting.selected_reactions == selected

        await client.stop()

    asyncio.run(scenario())


def test_edit_group_info_updates_reaction_setting_all(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "editGroupInfo"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "chat_reaction_setting": {"reaction_type": "All"},
                "updated_parameters": ["chat_reaction_setting"],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 2,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Hidden",
                            "event_messages": False,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": True,
                        },
                        "timestamp": "1774239075",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_reactions_all("g0HJRjv02cfa6363ca148b8d3351ca6d")

        assert result.group is not None
        assert result.group.chat_reaction_setting is not None
        assert result.group.chat_reaction_setting.reaction_type == "All"

        await client.stop()

    asyncio.run(scenario())


def test_edit_group_info_requires_at_least_one_supported_field():
    async def scenario():
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)

        try:
            await client.edit_group_info("g0HJRjv02cfa6363ca148b8d3351ca6d")
        except ValueError as exc:
            assert str(exc) == "At least one supported group field must be provided"
        else:
            raise AssertionError("Expected ValueError")

    asyncio.run(scenario())


def test_ban_group_member_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "banGroupMember"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "member_guid": "b0NMS0012c504de75ddb83f3bbc00f21",
                "action": "Set",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "timestamp": "1774239170",
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 1,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "chat_history_for_new_members": "Hidden",
                            "event_messages": False,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": True,
                        },
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.ban_group_member(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            "b0NMS0012c504de75ddb83f3bbc00f21",
        )

        assert result.timestamp == "1774239170"
        assert result.group is not None
        assert result.group.count_members == 1
        assert result.group.chat_history_for_new_members == "Hidden"
        assert result.group.chat_reaction_setting is not None
        assert result.group.chat_reaction_setting.reaction_type == "All"

        await client.stop()

    asyncio.run(scenario())


def test_unban_group_member_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "banGroupMember"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "member_guid": "b0NMS0012c504de75ddb83f3bbc00f21",
                "action": "Unset",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "timestamp": "1774239304",
                        "group": {
                            "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                            "group_title": "تست",
                            "count_members": 1,
                            "is_deleted": False,
                            "is_verified": False,
                            "slow_mode": 0,
                            "description": "شسی",
                            "chat_history_for_new_members": "Hidden",
                            "event_messages": False,
                            "chat_reaction_setting": {"reaction_type": "All"},
                            "is_restricted_content": True,
                        },
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.unban_group_member(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            "b0NMS0012c504de75ddb83f3bbc00f21",
        )

        assert result.timestamp == "1774239304"
        assert result.group is not None
        assert result.group.description == "شسی"
        assert result.group.chat_reaction_setting is not None
        assert result.group.chat_reaction_setting.reaction_type == "All"

        await client.stop()

    asyncio.run(scenario())


def test_set_group_admin_accepts_enum_access_list_and_returns_typed_result(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "setGroupAdmin"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                "action": "SetAdmin",
                "access_list": [
                    "ChangeInfo",
                    "PinMessages",
                    "DeleteGlobalAllMessages",
                    "BanMember",
                    "SetJoinLink",
                    "SetAdmin",
                    "SetMemberAccess",
                ],
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "in_chat_member": {
                            "member_type": "User",
                            "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                            "first_name": "Ehsan Davari",
                            "last_name": "",
                            "is_verified": False,
                            "is_deleted": False,
                            "promoted_by_object_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                            "promoted_by_object_type": "User",
                            "join_type": "Admin",
                            "username": "ehsndvr",
                            "online_time": {
                                "type": "Approximate",
                                "approximate_period": "Recently",
                            },
                        },
                        "timestamp": "1774239448",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_admin(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            "u0Crz5308d9ca919827a835fac44dbae",
            [
                GroupAdminAccess.CHANGE_INFO,
                GroupAdminAccess.PIN_MESSAGES,
                GroupAdminAccess.DELETE_GLOBAL_ALL_MESSAGES,
                GroupAdminAccess.BAN_MEMBER,
                GroupAdminAccess.SET_JOIN_LINK,
                GroupAdminAccess.SET_ADMIN,
                GroupAdminAccess.SET_MEMBER_ACCESS,
            ],
        )

        assert result.timestamp == "1774239448"
        assert result.in_chat_member is not None
        assert result.in_chat_member.member_guid == "u0Crz5308d9ca919827a835fac44dbae"
        assert result.in_chat_member.join_type == "Admin"
        assert result.in_chat_member.promoted_by_object_guid == "u0DiqTP0d4d36e090fb7060d540a33c7"
        assert result.in_chat_member.online_time is not None
        assert result.in_chat_member.online_time.approximate_period == "Recently"

        await client.stop()

    asyncio.run(scenario())


def test_update_group_admin_access_accepts_string_access_list(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "setGroupAdmin"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                "action": "SetAdmin",
                "access_list": [
                    "ChangeInfo",
                    "PinMessages",
                    "BanMember",
                    "SetJoinLink",
                    "SetAdmin",
                    "SetMemberAccess",
                ],
            }
            return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.update_group_admin_access(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            "u0Crz5308d9ca919827a835fac44dbae",
            [
                "ChangeInfo",
                "PinMessages",
                "BanMember",
                "SetJoinLink",
                "SetAdmin",
                "SetMemberAccess",
            ],
        )

        assert result.in_chat_member is None

        await client.stop()

    asyncio.run(scenario())


def test_unset_group_admin_uses_unset_admin_action(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "setGroupAdmin"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "member_guid": "u0Crz5308d9ca919827a835fac44dbae",
                "action": "UnsetAdmin",
            }
            return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.unset_group_admin(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            "u0Crz5308d9ca919827a835fac44dbae",
        )

        assert result.in_chat_member is None
        assert result.timestamp is None

        await client.stop()

    asyncio.run(scenario())


def test_set_group_default_access_accepts_enum_access_list(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "setGroupDefaultAccess"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "access_list": [
                    "ViewMembers",
                    "AddMember",
                    "SendMessages",
                    "ViewAdmins",
                ],
            }
            return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.set_group_default_access(
            "g0HJRjv02cfa6363ca148b8d3351ca6d",
            [
                GroupDefaultAccessPermission.VIEW_MEMBERS,
                GroupDefaultAccessPermission.ADD_MEMBER,
                GroupDefaultAccessPermission.SEND_MESSAGES,
                GroupDefaultAccessPermission.VIEW_ADMINS,
            ],
        )

        assert result is not None

        await client.stop()

    asyncio.run(scenario())


def test_request_change_object_owner_raises_invalid_auth_with_raw_payload(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "requestChangeObjectOwner"
            assert decrypted_request["input"] == {
                "object_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "new_owner_user_guid": "u0Crz5308d9ca919827a835fac44dbae",
            }
            return encrypt_response(
                {
                    "status": "ERROR_GENERIC",
                    "status_det": "INVALID_AUTH",
                    "client_show_message": {
                        "link": {
                            "type": "alert",
                            "alert_data": {
                                "message": "از زمان ورود شما بایستی 3 روز گذشته باشد.",
                            },
                        }
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        try:
            await client.request_change_object_owner(
                "g0HJRjv02cfa6363ca148b8d3351ca6d",
                "u0Crz5308d9ca919827a835fac44dbae",
            )
        except AuthKeyInvalid as exc:
            assert exc.status == "ERROR_GENERIC"
            assert exc.status_det == "INVALID_AUTH"
            assert exc.raw is not None
            assert exc.raw["client_show_message"]["link"]["alert_data"]["message"] == "از زمان ورود شما بایستی 3 روز گذشته باشد."
        else:
            raise AssertionError("Expected AuthKeyInvalid")

        await client.stop()

    asyncio.run(scenario())


def test_remove_group_raises_invalid_auth_with_raw_payload(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "removeGroup"
            assert decrypted_request["input"] == {
                "group_guid": "g0HJRjv02cfa6363ca148b8d3351ca6d",
            }
            return encrypt_response(
                {
                    "status": "ERROR_GENERIC",
                    "status_det": "INVALID_AUTH",
                    "client_show_message": {
                        "link": {
                            "type": "alert",
                            "alert_data": {
                                "message": "از زمان ورود شما بایستی 3 روز گذشته باشد.",
                            },
                        }
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        try:
            await client.remove_group("g0HJRjv02cfa6363ca148b8d3351ca6d")
        except AuthKeyInvalid as exc:
            assert exc.status == "ERROR_GENERIC"
            assert exc.status_det == "INVALID_AUTH"
            assert exc.raw is not None
            assert exc.raw["client_show_message"]["link"]["alert_data"]["message"] == "از زمان ورود شما بایستی 3 روز گذشته باشد."
        else:
            raise AssertionError("Expected AuthKeyInvalid")

        await client.stop()

    asyncio.run(scenario())


def test_receive_socket_update_decrypts_messenger_frames(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        class StubSocketTransport:
            async def handshake(self, auth, api_version="5", force_reconnect=False):
                return {"status": "OK", "status_det": "OK"}

            async def recv(self, timeout=None):
                return {
                    "type": "messenger",
                    "data_enc": encrypt_aes_cbc(
                        {
                            "chat_updates": [],
                            "message_updates": [
                                {
                                    "message_id": "1556351220500832",
                                    "action": "New",
                                    "message": {"message_id": "1556351220500832", "text": "sd", "type": "Text"},
                                    "object_guid": "u1",
                                    "state": "1773595631",
                                }
                            ],
                            "show_notifications": [],
                            "user_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                        },
                        "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb",
                    ),
                }

            async def close(self):
                return None

        client._socket_transport = StubSocketTransport()  # type: ignore[assignment]

        result = await client.receive_socket_update(timeout=0.1)

        assert result.user_guid == "u0DiqTP0d4d36e090fb7060d540a33c7"
        assert result.message_updates[0].message.text == "sd"
        assert result.message_updates[0].object_guid == "u1"

        await client.stop()

    asyncio.run(scenario())


def test_on_message_dispatches_message_handlers(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        seen = []

        @client.on_message()
        async def handler(app, message):
            seen.append((app.name, message.text, message.author_object_guid))

        update = client_module.SocketUpdates._parse(
            client,
            {
                "message_updates": [
                    {
                        "message_id": "1",
                        "action": "New",
                        "message": {
                            "message_id": "1",
                            "text": "hello",
                            "author_object_guid": "u123",
                            "type": "Text",
                        },
                    }
                ]
            },
        )

        await client._dispatch_socket_update(update)

        assert seen == [("test", "hello", "u123")]

        await client.stop()

    asyncio.run(scenario())


def test_on_message_handler_exception_does_not_stop_dispatch(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        seen = []

        @client.on_message()
        async def broken_handler(app, message):
            raise RuntimeError("boom")

        @client.on_message()
        async def healthy_handler(app, message):
            seen.append(message.text)

        update = client_module.SocketUpdates._parse(
            client,
            {
                "message_updates": [
                    {
                        "message_id": "1",
                        "action": "New",
                        "object_guid": "u123",
                        "message": {
                            "message_id": "1",
                            "text": "hello",
                            "author_object_guid": "u123",
                            "type": "Text",
                        },
                    }
                ]
            },
        )

        await client._dispatch_socket_update(update)

        assert seen == ["hello"]

        await client.stop()

    asyncio.run(scenario())


def test_message_reply_uses_send_message_with_reply_to(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        calls = []

        async def fake_send_message(self, object_guid, rnd, text, parse_mode=None, reply_to_message_id=None):
            calls.append(
                {
                    "object_guid": object_guid,
                    "rnd": rnd,
                    "text": text,
                    "parse_mode": parse_mode,
                    "reply_to_message_id": reply_to_message_id,
                }
            )
            return "sent"

        monkeypatch.setattr(Client, "send_message", fake_send_message)

        message = client_module.SocketUpdates._parse(
            client,
            {
                "message_updates": [
                    {
                        "message_id": "1",
                        "action": "New",
                        "object_guid": "u123",
                        "message": {
                            "message_id": "1",
                            "text": "hello",
                            "author_object_guid": "u123",
                            "type": "Text",
                        },
                    }
                ]
            },
        ).message_updates[0].message

        result = await message.reply("world")

        assert result == "sent"
        assert calls[0]["object_guid"] == "u123"
        assert calls[0]["text"] == "world"
        assert calls[0]["reply_to_message_id"] == "1"
        assert calls[0]["rnd"].isdigit()

        await client.stop()

    asyncio.run(scenario())


def test_on_message_filter_blocks_non_matching_messages(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()

        seen = []

        @client.on_message(filters.text & filters.private)
        async def handler(app, message):
            seen.append(message.text)

        update = client_module.SocketUpdates._parse(
            client,
            {
                "message_updates": [
                    {
                        "message_id": "1",
                        "action": "New",
                        "object_guid": "u123",
                        "type": "User",
                        "message": {
                            "message_id": "1",
                            "text": "hello",
                            "type": "Text",
                        },
                    },
                    {
                        "message_id": "2",
                        "action": "New",
                        "object_guid": "g123",
                        "type": "Group",
                        "message": {
                            "message_id": "2",
                            "text": "ignored",
                            "type": "Text",
                        },
                    },
                ]
            },
        )

        await client._dispatch_socket_update(update)

        assert seen == ["hello"]

        await client.stop()

    asyncio.run(scenario())


def test_filters_detect_media_and_regex():
    message = Message._parse(
        None,
        {
            "type": "FileInlineCaption",
            "text": "join: rubika.ir/joing/12345678901234567890123456789012",
            "file_inline": {"type": "Image"},
            "metadata": [{"type": "Bold"}],
            "chat_type": "User",
            "action": "New",
        },
    )

    assert filters.caption(None, message) is True
    assert filters.photo(None, message) is True
    assert filters.media(None, message) is True
    assert filters.group_link(None, message) is True
    assert filters.bold(None, message) is True
    assert (filters.caption & filters.private)(None, message) is True


def test_message_parses_rubino_sticker_voice_gif_and_live_payloads():
    rubino = Message._parse(
        None,
        {
            "type": "RubinoPost",
            "forwarded_from": {"type_from": "User", "message_id": "1", "object_guid": "u1"},
            "rubino_post_data": {"post_id": "p1", "post_profile_id": "pp1", "track_id": "Messenger"},
        },
    )
    sticker = Message._parse(
        None,
        {
            "type": "Sticker",
            "sticker": {
                "emoji_character": "x",
                "sticker_id": "s1",
                "file": {"file_id": "10", "type": "File"},
            },
        },
    )
    voice = Message._parse(
        None,
        {
            "type": "FileInline",
            "file_inline": {"file_id": 1, "type": "Voice", "file_name": "a.ogg"},
        },
    )
    live = Message._parse(
        None,
        {
            "type": "Live",
            "live_data": {
                "live_id": "l1",
                "title": "oo",
                "live_status": {"status": "Ready", "can_play": True},
            },
        },
    )

    assert rubino.rubino_post_data.post_id == "p1"
    assert rubino.forwarded_from.object_guid == "u1"
    assert sticker.sticker.file.file_id == "10"
    assert voice.file_inline.type == "Voice"
    assert live.live_data.live_status.status == "Ready"
    assert filters.rubino(None, rubino) is True
    assert filters.sticker(None, sticker) is True
    assert filters.voice(None, voice) is True
    assert filters.live(None, live) is True


def test_request_send_file_returns_typed_descriptor(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            assert decrypted_request["method"] == "requestSendFile"
            assert decrypted_request["input"] == {
                "file_name": "voice.ogg",
                "size": 1654,
                "mime": "ogg",
            }
            return encrypt_response(
                {
                    "status": "OK",
                    "status_det": "OK",
                    "data": {
                        "id": "87998036915657",
                        "dc_id": "491",
                        "access_hash_send": "euthauxjfybzjbaaymlitbhpio8651",
                        "upload_url": "https://upmessenger491.iranlms.ir/UploadFile.ashx",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.request_send_file("voice.ogg", 1654, "ogg")

        assert result.id == "87998036915657"
        assert result.dc_id == "491"
        assert result.access_hash_send == "euthauxjfybzjbaaymlitbhpio8651"
        assert result.upload_url == "https://upmessenger491.iranlms.ir/UploadFile.ashx"

        await client.stop()

    asyncio.run(scenario())


def build_test_ogg_opus(duration_ms: int) -> bytes:
    sample_count = int(duration_ms * 48)

    def ogg_page(granule_position: int, sequence: int, packet: bytes) -> bytes:
        segments = []
        remaining = len(packet)
        if remaining == 0:
            segments.append(0)
        else:
            while remaining >= 255:
                segments.append(255)
                remaining -= 255
            segments.append(remaining)

        header = (
            b"OggS"
            + bytes([0, 0])
            + granule_position.to_bytes(8, "little", signed=False)
            + (1).to_bytes(4, "little", signed=False)
            + sequence.to_bytes(4, "little", signed=False)
            + (0).to_bytes(4, "little", signed=False)
            + bytes([len(segments)])
        )
        return header + bytes(segments) + packet

    opus_head = b"OpusHead" + bytes([1, 1]) + (0).to_bytes(2, "little") + (48000).to_bytes(4, "little") + (0).to_bytes(2, "little", signed=True) + bytes([0])
    audio_packet = b"voice-payload"
    return ogg_page(0, 0, opus_head) + ogg_page(sample_count, 1, audio_packet)


def test_send_voice_uploads_and_sends_file_inline(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        temp_path = Path.cwd() / f"_voice_{uuid.uuid4().hex}.ogg"
        temp_path.write_bytes(b"OggS-test")

        async def upload_file(self, *, auth, descriptor, path, progress=None, progress_args=()):
            assert auth == "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
            assert descriptor.id == "87998036915657"
            assert Path(path) == temp_path
            return client_module.UploadDescriptor(
                id=descriptor.id,
                dc_id=descriptor.dc_id,
                access_hash_send=descriptor.access_hash_send,
                access_hash_rec="1827275907694936106542107050922026031521",
                upload_url=descriptor.upload_url,
            )

        monkeypatch.setattr(client_module.UploadTransport, "upload_file", upload_file)

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            method = decrypted_request["method"]

            if method == "requestSendFile":
                return encrypt_response(
                    {
                        "status": "OK",
                        "status_det": "OK",
                        "data": {
                            "id": "87998036915657",
                            "dc_id": "491",
                            "access_hash_send": "euthauxjfybzjbaaymlitbhpio8651",
                            "upload_url": "https://upmessenger491.iranlms.ir/UploadFile.ashx",
                        },
                    },
                    auth,
                )

            if method == "sendMessage":
                assert decrypted_request["input"]["object_guid"] == "u123"
                assert decrypted_request["input"]["file_inline"] == {
                    "file_name": temp_path.name,
                    "time": 720,
                    "size": temp_path.stat().st_size,
                    "type": "Voice",
                    "dc_id": "491",
                    "file_id": "87998036915657",
                    "mime": "ogg",
                    "access_hash_rec": "1827275907694936106542107050922026031521",
                }
                assert "text" not in decrypted_request["input"]
                return encrypt_response(
                    {
                        "status": "OK",
                        "status_det": "OK",
                        "data": {
                            "message_update": {
                                "message_id": "1556497285304832",
                                "action": "New",
                                "message": {
                                    "message_id": "1556497285304832",
                                    "file_inline": {
                                        "file_id": 87998036915657,
                                        "mime": "ogg",
                                        "dc_id": 491,
                                        "access_hash_rec": "1827275907694936106542107050922026031521",
                                        "file_name": temp_path.name,
                                        "time": 0,
                                        "size": temp_path.stat().st_size,
                                        "type": "Voice",
                                    },
                                    "time": "1773599154",
                                    "is_edited": False,
                                    "type": "FileInline",
                                    "author_type": "User",
                                    "author_object_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                    "allow_transcription": False,
                                },
                                "updated_parameters": [],
                                "timestamp": "1773599154",
                                "prev_message_id": "1556479276978832",
                                "object_guid": "u123",
                                "type": "User",
                                "state": "1773599094",
                                "is_scheduled": False,
                            },
                            "status": "OK",
                            "chat_update": {
                                "object_guid": "u123",
                                "action": "Edit",
                                "chat": {
                                    "time_string": "177359915400001556497285304832",
                                    "last_message": {
                                        "message_id": "1556497285304832",
                                        "type": "Other",
                                        "text": "پیام صوتی",
                                        "author_object_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                        "is_mine": True,
                                        "author_title": "شما",
                                        "author_type": "User",
                                    },
                                    "last_seen_peer_mid": "1556482278263832",
                                    "status": "Active",
                                    "time": 1773599154,
                                    "last_message_id": "1556497285304832",
                                },
                                "updated_parameters": [
                                    "last_message_id",
                                    "last_message",
                                    "status",
                                    "time_string",
                                    "last_seen_peer_mid",
                                    "time",
                                ],
                                "timestamp": "1773599154",
                                "type": "User",
                            },
                        },
                    },
                    auth,
                )

            raise AssertionError(f"Unexpected method: {method}")

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.send_voice("u123", temp_path, duration_ms=720)

        assert result.message_update.message.file_inline.type == "Voice"
        assert result.message_update.object_guid == "u123"
        assert result.chat_update.object_guid == "u123"

        temp_path.unlink(missing_ok=True)
        await client.stop()

    asyncio.run(scenario())


def test_send_voice_derives_duration_from_ogg_opus(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        temp_path = Path.cwd() / f"_voice_auto_{uuid.uuid4().hex}.ogg"
        temp_path.write_bytes(build_test_ogg_opus(720))

        async def upload_file(self, *, auth, descriptor, path, progress=None, progress_args=()):
            return client_module.UploadDescriptor(
                id=descriptor.id,
                dc_id=descriptor.dc_id,
                access_hash_send=descriptor.access_hash_send,
                access_hash_rec="1827275907694936106542107050922026031521",
                upload_url=descriptor.upload_url,
            )

        monkeypatch.setattr(client_module.UploadTransport, "upload_file", upload_file)

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            method = decrypted_request["method"]

            if method == "requestSendFile":
                return encrypt_response(
                    {
                        "status": "OK",
                        "status_det": "OK",
                        "data": {
                            "id": "87998036915657",
                            "dc_id": "491",
                            "access_hash_send": "euthauxjfybzjbaaymlitbhpio8651",
                            "upload_url": "https://upmessenger491.iranlms.ir/UploadFile.ashx",
                        },
                    },
                    auth,
                )

            if method == "sendMessage":
                assert decrypted_request["input"]["file_inline"]["time"] == 720.0
                return encrypt_response(
                    {
                        "status": "OK",
                        "status_det": "OK",
                        "data": {
                            "message_update": {
                                "message_id": "1556497285304832",
                                "action": "New",
                                "message": {
                                    "message_id": "1556497285304832",
                                    "file_inline": {
                                        "file_id": 87998036915657,
                                        "mime": "ogg",
                                        "dc_id": 491,
                                        "access_hash_rec": "1827275907694936106542107050922026031521",
                                        "file_name": temp_path.name,
                                        "time": 720.0,
                                        "size": temp_path.stat().st_size,
                                        "type": "Voice",
                                    },
                                    "time": "1773599154",
                                    "is_edited": False,
                                    "type": "FileInline",
                                    "author_type": "User",
                                    "author_object_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                    "allow_transcription": False,
                                },
                                "updated_parameters": [],
                                "timestamp": "1773599154",
                                "prev_message_id": "1556479276978832",
                                "object_guid": "u123",
                                "type": "User",
                                "state": "1773599094",
                                "is_scheduled": False,
                            },
                            "status": "OK",
                            "chat_update": {
                                "object_guid": "u123",
                                "action": "Edit",
                                "chat": {
                                    "time_string": "177359915400001556497285304832",
                                    "last_message": {
                                        "message_id": "1556497285304832",
                                        "type": "Other",
                                        "text": "voice",
                                        "author_object_guid": "u0DiqTP0d4d36e090fb7060d540a33c7",
                                        "is_mine": True,
                                        "author_title": "me",
                                        "author_type": "User",
                                    },
                                    "last_seen_peer_mid": "1556482278263832",
                                    "status": "Active",
                                    "time": 1773599154,
                                    "last_message_id": "1556497285304832",
                                },
                                "updated_parameters": [
                                    "last_message_id",
                                    "last_message",
                                    "status",
                                    "time_string",
                                    "last_seen_peer_mid",
                                    "time",
                                ],
                                "timestamp": "1773599154",
                                "type": "User",
                            },
                        },
                    },
                    auth,
                )

            raise AssertionError(f"Unexpected method: {method}")

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.send_voice("u123", temp_path)

        assert result.message_update.message.file_inline.type == "Voice"

        temp_path.unlink(missing_ok=True)
        await client.stop()

    asyncio.run(scenario())



def test_client_download_file_in_memory(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        async def fake_download_file(self, **kwargs):
            assert kwargs["auth"] == "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb"
            assert kwargs["file_id"] == 87996041918445
            assert kwargs["dc_id"] == 435
            assert kwargs["access_hash_rec"] == "6704352162326267560942489985562026031521"
            assert kwargs["file_size"] == 7788
            assert kwargs["in_memory"] is True
            return b"voice-bytes"

        monkeypatch.setattr(client_module.DownloadTransport, "download_file", fake_download_file)

        message = Message._parse(
            client,
            {
                "message_id": "1",
                "type": "FileInline",
                "file_inline": {
                    "file_id": 87996041918445,
                    "mime": "ogg",
                    "dc_id": 435,
                    "access_hash_rec": "6704352162326267560942489985562026031521",
                    "file_name": "voice.ogg",
                    "time": 1000,
                    "size": 7788,
                    "type": "Voice",
                },
            },
        )

        result = await client.download_file(message, in_memory=True)

        assert result == b"voice-bytes"

        await client.stop()

    asyncio.run(scenario())


def test_message_download_uses_bound_client(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        target = Path.cwd() / f"_downloads_{uuid.uuid4().hex}"

        async def fake_download_file(self, file, path=None, in_memory=False, file_name=None, progress=None, progress_args=()):
            assert getattr(file.file_inline, "file_name", None) == "voice.ogg"
            assert path == target
            assert in_memory is False
            output = target / "voice.ogg"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"voice-bytes")
            return output

        monkeypatch.setattr(Client, "download_file", fake_download_file)

        message = client_module.SocketUpdates._parse(
            client,
            {
                "message_updates": [
                    {
                        "message_id": "1",
                        "action": "New",
                        "object_guid": "u123",
                        "message": {
                            "message_id": "1",
                            "type": "FileInline",
                            "file_inline": {
                                "file_id": 87996041918445,
                                "mime": "ogg",
                                "dc_id": 435,
                                "access_hash_rec": "6704352162326267560942489985562026031521",
                                "file_name": "voice.ogg",
                                "time": 1000,
                                "size": 7788,
                                "type": "Voice",
                            },
                        },
                    }
                ]
            },
        ).message_updates[0].message

        result = await message.download(path=target)

        assert result.read_bytes() == b"voice-bytes"
        result.unlink(missing_ok=True)
        target.rmdir()

        await client.stop()

    asyncio.run(scenario())



def test_send_music_uploads_and_sends_file_inline(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        temp_path = Path.cwd() / f"_music_{uuid.uuid4().hex}.mp3"
        temp_path.write_bytes(b"MP3DATA")
        progress_calls = []

        async def upload_file(self, *, auth, descriptor, path, progress=None, progress_args=()):
            if progress is not None:
                result = progress(7, 7, *progress_args)
                if asyncio.iscoroutine(result):
                    await result
            return client_module.UploadDescriptor(
                id=descriptor.id,
                dc_id=descriptor.dc_id,
                access_hash_send=descriptor.access_hash_send,
                access_hash_rec="rec-music",
                upload_url=descriptor.upload_url,
            )

        monkeypatch.setattr(client_module.UploadTransport, "upload_file", upload_file)

        def progress(current, total, label):
            progress_calls.append((current, total, label))

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            method = decrypted_request["method"]
            if method == "requestSendFile":
                return encrypt_response(
                    {
                        "status": "OK",
                        "status_det": "OK",
                        "data": {
                            "id": "88001038289473",
                            "dc_id": "408",
                            "access_hash_send": "zaweshaqbsahhnmqtsobujloqr8651",
                            "upload_url": "https://upmessenger408.iranlms.ir/UploadFile.ashx",
                        },
                    },
                    auth,
                )
            if method == "sendMessage":
                assert decrypted_request["input"]["file_inline"] == {
                    "file_name": temp_path.name,
                    "size": temp_path.stat().st_size,
                    "type": "Music",
                    "dc_id": "408",
                    "file_id": "88001038289473",
                    "mime": "mp3",
                    "access_hash_rec": "rec-music",
                    "time": 1000,
                }
                return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)
            raise AssertionError(f"Unexpected method: {method}")

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        await client.send_music("u123", temp_path, duration_ms=1000, progress=progress, progress_args=("music",))

        assert progress_calls == [(7, 7, "music")]
        temp_path.unlink(missing_ok=True)
        await client.stop()

    asyncio.run(scenario())


def test_send_video_uploads_and_sends_file_inline(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_socket_handshake=False, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        temp_path = Path.cwd() / f"_video_{uuid.uuid4().hex}.mp4"
        temp_path.write_bytes(b"MP4DATA")

        async def upload_file(self, *, auth, descriptor, path, progress=None, progress_args=()):
            return client_module.UploadDescriptor(
                id=descriptor.id,
                dc_id=descriptor.dc_id,
                access_hash_send=descriptor.access_hash_send,
                access_hash_rec="rec-video",
                upload_url=descriptor.upload_url,
            )

        monkeypatch.setattr(client_module.UploadTransport, "upload_file", upload_file)

        async def send_payload(payload):
            auth = await client.storage.auth()
            decrypted_request = client._decrypt_response({"data_enc": payload["data_enc"]}, auth)
            method = decrypted_request["method"]
            if method == "requestSendFile":
                return encrypt_response(
                    {
                        "status": "OK",
                        "status_det": "OK",
                        "data": {
                            "id": "88001038289474",
                            "dc_id": "409",
                            "access_hash_send": "video-send-hash",
                            "upload_url": "https://upmessenger409.iranlms.ir/UploadFile.ashx",
                        },
                    },
                    auth,
                )
            if method == "sendMessage":
                assert decrypted_request["input"]["text"] == "caption"
                assert decrypted_request["input"]["file_inline"] == {
                    "file_name": temp_path.name,
                    "size": temp_path.stat().st_size,
                    "type": "Video",
                    "dc_id": "409",
                    "file_id": "88001038289474",
                    "mime": "mp4",
                    "access_hash_rec": "rec-video",
                    "time": 2000,
                    "width": 480,
                    "height": 852,
                    "is_round": False,
                    "is_spoil": False,
                }
                return encrypt_response({"status": "OK", "status_det": "OK", "data": {}}, auth)
            raise AssertionError(f"Unexpected method: {method}")

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        await client.send_video("u123", temp_path, duration_ms=2000, width=480, height=852, text="caption")

        temp_path.unlink(missing_ok=True)
        await client.stop()

    asyncio.run(scenario())



def test_update_listener_recovers_after_transport_error(monkeypatch):
    async def scenario():
        monkeypatch.setattr(client_module.DcDiscovery, "fetch_dcs", fake_fetch_dcs)
        client = Client("test", in_memory=True, enable_register_device=False)
        await client.start()
        await client.storage.set_auth("zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb")

        seen = []

        @client.on_message()
        async def handler(app, message):
            seen.append(message.text)
            app._is_connected = False

        calls = {"recv": 0}

        class StubSocketTransport:
            async def handshake(self, auth, api_version="5", force_reconnect=False):
                return {"status": "OK", "status_det": "OK"}

            async def recv(self, timeout=None):
                calls["recv"] += 1
                if calls["recv"] == 1:
                    raise client_module.TransportError("Socket connection dropped")
                return {
                    "type": "messenger",
                    "data_enc": encrypt_aes_cbc(
                        {
                            "chat_updates": [],
                            "message_updates": [
                                {
                                    "message_id": "1",
                                    "action": "New",
                                    "message": {"message_id": "1", "text": "hello", "type": "Text"},
                                    "object_guid": "u1",
                                    "state": "1",
                                }
                            ],
                            "show_notifications": [],
                            "user_guid": "u0",
                        },
                        "zjbyfpwfoxtvhfgdlohvtjcczxxqhsnb",
                    ),
                }

            async def close(self):
                return None

        client._socket_transport = StubSocketTransport()  # type: ignore[assignment]
        task = asyncio.create_task(client._update_listener_loop())
        await asyncio.wait_for(task, timeout=2)

        assert seen == ["hello"]

        await client.stop()

    asyncio.run(scenario())
