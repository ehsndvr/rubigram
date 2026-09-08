"""An in-process stand-in for the Rubika servers used by the client tests.

``FakeRubika`` replaces ``HttpTransport``: it decrypts every envelope with the
same AES scheme the real server uses, records ``(method, input)`` pairs and
answers from a small response table.  ``FakeServices`` replaces the plain-JSON
``JsonTransport`` (``getBaseInfo``, Rubino) and ``FakeDiscovery`` answers
``getDCs``.  No socket is opened anywhere.
"""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from rubigram.client import client as client_module
from rubigram.crypto import caesar_decode, change_auth_type, decrypt_aes_cbc, encrypt_aes_cbc

FIXTURES = Path(__file__).parent / "fixtures" / "rubika"

DCS_PAYLOAD: Dict[str, Any] = {
    "status": "OK",
    "status_det": "OK",
    "data": {
        "default_api_urls": ["https://messengerg2c777.iranlms.ir", "https://messengerg2c888.iranlms.ir"],
        "default_sockets": ["wss://nsocket10.iranlms.ir:80"],
        "storages": {"1": "https://messanger.iranlms.ir/GetFile.ashx", "491": "https://messanger491.iranlms.ir/GetFile.ashx"},
        "default_cdn_urls": {"PR": ["https://msgcdn1.iranlms.ir/GetFile"]},
    },
}

BASE_INFO_PAYLOAD: Dict[str, Any] = {
    "status": "OK",
    "status_det": "OK",
    "data": {
        "suggested_urls": {"suggested_rubino": "https://rubino1.iranlms.ir", "suggested_wallet": "https://wallet1.iranlms.ir"},
        "services": [],
    },
}

FAKE_AUTH = "a" * 32
FAKE_USER_GUID = "u0EXAMPLE00000000000000000000001"
FAKE_PHONE = "98" + "9" * 10  # synthetic; never a real number
FAKE_CODE = "0" * 5


def fixture(name: str) -> Dict[str, Any]:
    """The recorded server answer (``data`` part) of ``tests/fixtures/rubika/<name>.json``."""
    payload = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    response = payload[1] if isinstance(payload, list) else payload
    return response["data"] if isinstance(response, dict) and "data" in response else response


def rsa_wrap(public_key_pem_or_b64: str, value: str) -> str:
    """Encrypt ``value`` the way the server wraps the session auth (PKCS#1 v1.5).

    Accepts a PEM public key or the login form of it (``change_auth_type(base64(PEM))``).
    """
    raw = public_key_pem_or_b64
    if "BEGIN" not in raw:
        raw = base64.b64decode(change_auth_type(raw)).decode("utf-8")
    public_key = serialization.load_pem_public_key(raw.encode("utf-8"))
    assert isinstance(public_key, RSAPublicKey)
    return base64.b64encode(public_key.encrypt(value.encode("utf-8"), asym_padding.PKCS1v15())).decode("utf-8")


Responder = Callable[[Dict[str, Any]], Any]


class FakeRubika:
    """Encrypted RPC endpoint.  ``responses[method]`` is a dict (data), a list of
    answers consumed in order, a callable ``input -> answer`` or an exception.

    An answer that is a dict with a ``status`` other than ``OK`` is returned as
    the *inner* (decrypted) error; wrap it in ``Outer(...)`` to make it the
    outer HTTP-level envelope error instead.
    """

    class Outer:
        def __init__(self, payload: Dict[str, Any]):
            self.payload = payload

    def __init__(self, *, auth: str = FAKE_AUTH):
        self.auth = auth
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self.envelopes: List[Dict[str, Any]] = []
        self.payloads: List[Dict[str, Any]] = []
        self.responses: Dict[str, Any] = {}
        self.closed = False
        self.pool = _FakePool("https://messengerg2c777.iranlms.ir")
        self.last_request = None

    # -- HttpTransport interface ------------------------------------------------

    async def send(self, payload: Dict[str, Any], *, timeout: Optional[float] = None, retries: Optional[int] = None) -> Dict[str, Any]:
        self.payloads.append(payload)
        if "tmp_session" in payload:
            key = payload["tmp_session"]
        else:
            key = caesar_decode(payload["auth"])
            assert key == self.auth, "envelope was encrypted with an unknown auth"
            assert payload.get("sign"), "auth envelopes must be signed"
        data_obj = decrypt_aes_cbc(payload["data_enc"], key)
        self.envelopes.append(data_obj)
        method = data_obj["method"]
        self.calls.append((method, data_obj.get("input", {})))
        answer = self._answer(method, data_obj.get("input", {}))
        if isinstance(answer, FakeRubika.Outer):
            return answer.payload
        if isinstance(answer, dict) and str(answer.get("status", "OK")).startswith("ERROR"):
            inner = answer
        else:
            inner = {"status": "OK", "status_det": "OK", "data": answer}
        return {"status": "OK", "status_det": "OK", "data_enc": encrypt_aes_cbc(inner, key)}

    async def close(self) -> None:
        self.closed = True

    def use_client(self, client: Any) -> None:  # pragma: no cover - interface parity
        pass

    # -- helpers ---------------------------------------------------------------------

    def _answer(self, method: str, input_data: Dict[str, Any]) -> Any:
        if method not in self.responses:
            path = FIXTURES / f"{method}.json"
            if path.exists():
                return fixture(method)
            return {}
        answer = self.responses[method]
        if isinstance(answer, list):
            if not answer:
                raise AssertionError(f"no queued answer left for {method}")
            answer = answer.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            answer = answer(input_data)
        return answer

    def methods(self) -> List[str]:
        return [method for method, _ in self.calls]

    def inputs(self, method: str) -> List[Dict[str, Any]]:
        return [input_data for name, input_data in self.calls if name == method]


class FakeServices:
    """Plain-JSON endpoint (``getBaseInfo``, Rubino, web apps)."""

    def __init__(self):
        self.calls: List[Tuple[str, Dict[str, Any], Optional[str]]] = []
        self.responses: Dict[str, Any] = {"getBaseInfo": BASE_INFO_PAYLOAD}
        self.closed = False

    async def send(
        self, payload: Dict[str, Any], *, url: Optional[str] = None, timeout: Optional[float] = None, retries: Optional[int] = None
    ) -> Dict[str, Any]:
        method = payload.get("method", "")
        self.calls.append((method, payload, url))
        answer: Any = self.responses.get(method, {"status": "OK", "status_det": "OK", "data": {}})
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            answer = answer(payload)
        return answer

    async def close(self) -> None:
        self.closed = True


class FakeDiscovery:
    def __init__(self, *args: Any, **kwargs: Any):
        self.dcs_calls = 0

    async def fetch_dcs(self) -> Dict[str, Any]:
        self.dcs_calls += 1
        return DCS_PAYLOAD

    async def close(self) -> None:
        pass


class _FakePool:
    def __init__(self, url: str):
        self.url = url

    def get_current(self) -> str:
        return self.url


class FakeBotTransport:
    """Stands in for ``BotTransport``: records calls and answers from a table."""

    def __init__(self, token: str = "1:fake", **kwargs: Any):
        self.token = token
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self.responses: Dict[str, Any] = {}
        self.uploads: List[Tuple[str, str]] = []
        self.downloads: List[Dict[str, Any]] = []
        self.closed = False

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        self.calls.append((method, dict(payload or {})))
        answer = self.responses.get(method, {})
        if isinstance(answer, list):
            answer = answer.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            answer = answer(payload or {})
        return answer

    @staticmethod
    def unwrap(response: Any, *, method: Optional[str] = None) -> Any:
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    async def upload_file(self, upload_url: str, path: Any, **kwargs: Any) -> Dict[str, Any]:
        self.uploads.append((upload_url, str(path)))
        return {"status": "OK", "data": {"file_id": "file-42"}}

    async def download_file(self, url: str, *, path: Any = None, in_memory: bool = False) -> Any:
        self.downloads.append({"url": url, "path": path, "in_memory": in_memory})
        if in_memory:
            return b"bot-bytes"
        Path(path).write_bytes(b"bot-bytes")
        return Path(path)

    async def close(self) -> None:
        self.closed = True

    def methods(self) -> List[str]:
        return [method for method, _ in self.calls]

    def payload(self, method: str) -> Dict[str, Any]:
        for name, payload in self.calls:
            if name == method:
                return payload
        raise AssertionError(f"{method} was not called")


def install(
    monkeypatch: Any, *, rubika: Optional[FakeRubika] = None, services: Optional[FakeServices] = None
) -> Tuple[FakeRubika, FakeServices]:
    """Route every transport ``Client`` builds to the fakes."""
    rubika = rubika or FakeRubika()
    services = services or FakeServices()
    monkeypatch.setattr(client_module, "DcDiscovery", FakeDiscovery)
    monkeypatch.setattr(client_module, "HttpTransport", lambda *args, **kwargs: rubika)
    monkeypatch.setattr(client_module, "JsonTransport", lambda *args, **kwargs: services)
    monkeypatch.setattr(client_module, "BotTransport", lambda token, **kwargs: FakeBotTransport(token, **kwargs))
    return rubika, services


async def seed_session(client: Any, *, auth: str = FAKE_AUTH, user_guid: str = FAKE_USER_GUID, registered: bool = True) -> None:
    """Pre-populate an in-memory storage with a logged-in, registered session."""
    await client.storage.open()
    await client.storage.set_auth(auth)
    await client.storage.set_user_guid(user_guid)
    await client.storage.set_registered_device(registered)
    await client.storage.set_registered_device_version(client.app_version if registered else None)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


__all__ = [
    "BASE_INFO_PAYLOAD",
    "DCS_PAYLOAD",
    "FAKE_AUTH",
    "FAKE_CODE",
    "FAKE_PHONE",
    "FAKE_USER_GUID",
    "FakeBotTransport",
    "FakeDiscovery",
    "FakeRubika",
    "FakeServices",
    "fixture",
    "install",
    "rsa_wrap",
    "run",
    "seed_session",
]
