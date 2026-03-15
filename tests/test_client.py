import asyncio
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

import rubigram.client as client_module
from rubigram.client import Client
from rubigram.crypto import encrypt_aes_cbc, export_public_key_for_login, rsa_key_generate
from rubigram.exceptions import AuthKeyInvalid, CodeIsInvalid, InvalidInput, LoginRequired, RegisterDeviceRequired
from rubigram.raw.methods import GetUserInfo
from rubigram.storage import MemoryStorage


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
                        "user": {
                            "user_guid": "u123",
                            "first_name": "King",
                            "phone": "989912398434",
                            "online_time": {"type": "Exact", "exact_time": 1773593199},
                        },
                        "chat": {
                            "object_guid": "u123",
                            "status": "Active",
                            "last_message": {"message_id": "1", "text": "hello", "type": "Text"},
                        },
                        "timestamp": "1773593199",
                    },
                },
                auth,
            )

        client._transport.send_payload = send_payload  # type: ignore[method-assign]

        result = await client.get_user_info("u123")

        assert result.user.user_guid == "u123"
        assert result.user.online_time.type == "Exact"
        assert result.chat.object_guid == "u123"
        assert result.chat.last_message.text == "hello"
        assert result.timestamp == "1773593199"

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
