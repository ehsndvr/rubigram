import asyncio
import json
from typing import Any, cast

import httpx
import pytest

from rubigram.enums import DcType
from rubigram.errors import InvalidAuth, NetworkError, RequestTimeout, TransportError
from rubigram.network import (
    BotTransport,
    DcDiscovery,
    DcRepository,
    DownloadTransport,
    HttpTransport,
    JsonTransport,
    RetryPolicy,
    SocketTransport,
    Transport,
    UploadTransport,
    UrlPool,
)
from rubigram.network.headers import CHROME_USER_AGENT, build_client_hints, build_rpc_headers, build_websocket_headers
from rubigram.network.retry import run_with_retries
from rubigram.types import UploadDescriptor


def run(coro):
    return asyncio.run(coro)


def no_sleep(policy: RetryPolicy) -> RetryPolicy:
    return RetryPolicy(delays=tuple(0.0 for _ in policy.delays), timeout=policy.timeout, max_retries=policy.max_retries)


# ---------------------------------------------------------------------------
# Transport enum / retry policy / url pool
# ---------------------------------------------------------------------------


def test_transport_coerce_accepts_strings_and_members():
    assert Transport.coerce("ws") is Transport.WS
    assert Transport.coerce("HTTP") is Transport.HTTP
    assert Transport.coerce(Transport.WS) is Transport.WS
    assert Transport.coerce("websocket") is Transport.WS
    assert Transport.WS == "ws"
    for bad in ("grpc", "", None, 3):
        with pytest.raises(ValueError):
            Transport.coerce(cast(Any, bad))


def test_retry_policy_matches_web_client_ladder_and_overrides():
    policy = RetryPolicy()
    assert policy.delays == (0.0, 2.0, 3.0, 5.0, 10.0)
    assert policy.retries == 5
    assert policy.attempts == 6
    assert policy.timeout == 20.0
    assert policy.delay_for(9) == 10.0
    capped = policy.with_overrides(retries=2, timeout=7)
    assert capped.retries == 2 and capped.timeout == 7.0
    assert policy.with_overrides(retries=0).attempts == 1


def test_run_with_retries_stops_at_non_retryable_and_exhaustion():
    calls = []

    async def attempt(index):
        calls.append(index)
        raise ValueError("boom")

    async def fake_sleep(_):
        return None

    with pytest.raises(ValueError):
        run(run_with_retries(RetryPolicy(max_retries=2), attempt, retryable=lambda exc: True, sleep=fake_sleep))
    assert calls == [0, 1, 2]
    calls.clear()
    with pytest.raises(ValueError):
        run(run_with_retries(RetryPolicy(), attempt, retryable=lambda exc: False, sleep=fake_sleep))
    assert calls == [0]


def test_url_pool_rotation_lock_and_replace():
    pool = UrlPool(["https://a", "https://b", "https://c"], switch_lock=60)
    assert pool.get_current() == "https://a"
    assert pool.rotate() == "https://b"
    assert pool.rotate() == "https://b"  # locked
    assert pool.force_rotate() == "https://c"
    pool.replace(["https://c", "https://d"])
    assert pool.get_current() == "https://c"
    pool.replace(["https://x"])
    assert pool.get_current() == "https://x"
    with pytest.raises(TransportError):
        UrlPool([]).get_current()
    assert UrlPool(["https://a", "https://a"]).count == 1


# ---------------------------------------------------------------------------
# HTTP transport
# ---------------------------------------------------------------------------


def _mock_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_http_transport_sends_text_plain_body_and_rotates_on_timeout():
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), request.headers.get("content-type"), request.content.decode()))
        if len(seen) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json={"status": "OK", "status_det": "OK"})

    transport = HttpTransport(
        ["https://messengerg2c1.iranlms.ir", "https://messengerg2c2.iranlms.ir"], retry_policy=no_sleep(RetryPolicy())
    )
    transport.use_client(_mock_client(handler))
    result = run(transport.send({"api_version": "6", "auth": "x", "data_enc": "abc", "sign": "sig"}))

    assert result["status"] == "OK"
    assert seen[0][0] == "https://messengerg2c1.iranlms.ir/"
    assert seen[1][0] == "https://messengerg2c2.iranlms.ir/"
    assert seen[0][1] == "text/plain"
    assert json.loads(seen[0][2]) == {"api_version": "6", "auth": "x", "data_enc": "abc", "sign": "sig"}
    assert transport.last_request is not None and transport.last_request.headers["user-agent"] == CHROME_USER_AGENT
    run(transport.close())


def test_http_transport_retries_5xx_and_invalid_json_but_not_4xx():
    responses = [httpx.Response(502, text="bad gateway"), httpx.Response(200, text="not json"), httpx.Response(200, json={"status": "OK"})]

    async def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    transport = HttpTransport(["https://a.iranlms.ir"], retry_policy=no_sleep(RetryPolicy()))
    transport.use_client(_mock_client(handler))
    assert run(transport.send({"x": 1}))["status"] == "OK"

    async def forbidden(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="nope")

    transport.use_client(_mock_client(forbidden))
    with pytest.raises(TransportError):
        run(transport.send({"x": 1}))


def test_http_transport_raises_request_timeout_after_ladder_and_refreshes_urls_once():
    attempts = []
    refreshes = []

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(str(request.url))
        raise httpx.ConnectTimeout("down", request=request)

    async def refresh():
        refreshes.append(1)
        return ["https://fresh.iranlms.ir"]

    transport = HttpTransport(
        ["https://a.iranlms.ir", "https://b.iranlms.ir"], retry_policy=no_sleep(RetryPolicy(max_retries=3)), refresh_urls=refresh
    )
    transport.use_client(_mock_client(handler))
    with pytest.raises(RequestTimeout):
        run(transport.send({"x": 1}))
    assert len(attempts) == 4
    assert refreshes == [1]
    assert "https://fresh.iranlms.ir/" in attempts


def test_http_transport_retries_zero_disables_retry():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("down", request=request)

    transport = HttpTransport(["https://a.iranlms.ir", "https://b.iranlms.ir"], retry_policy=no_sleep(RetryPolicy()))
    transport.use_client(_mock_client(handler))
    with pytest.raises(NetworkError):
        run(transport.send({"x": 1}, retries=0))
    assert calls == [1]


def test_json_transport_posts_json_and_honours_url_override():
    seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), request.headers.get("content-type"), json.loads(request.content)))
        return httpx.Response(200, json={"status": "OK", "data": {"posts": []}})

    transport = JsonTransport(["https://rubino1.iranlms.ir/"])
    transport.use_client(_mock_client(handler))
    run(transport.send({"method": "getProfilePosts"}))
    run(transport.send({"method": "getBaseInfo"}, url="https://servicesbase.iranlms.ir/"))
    assert seen[0] == ("https://rubino1.iranlms.ir/", "application/json", {"method": "getProfilePosts"})
    assert seen[1][0] == "https://servicesbase.iranlms.ir/"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

DCS_PAYLOAD = {
    "status": "OK",
    "status_det": "OK",
    "data": {
        "default_api_urls": ["https://messengerg2c777.iranlms.ir", "messengerg2c888.iranlms.ir"],
        "default_sockets": ["wss://nsocket10.iranlms.ir:80/"],
        "storages": {"1": "https://messanger.iranlms.ir/GetFile.ashx", "2": "https://messanger2.iranlms.ir/GetFile.ashx"},
        "default_cdn_urls": {"PR": ["https://msgcdn1.iranlms.ir/GetFile"]},
    },
}


def test_dc_discovery_fetches_dcs_with_plain_json_and_api_version_4():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        seen["content_type"] = request.headers.get("content-type")
        return httpx.Response(200, json=DCS_PAYLOAD)

    discovery = DcDiscovery()
    discovery._client = _mock_client(handler)
    payload = run(discovery.fetch_dcs())
    assert payload["data"]["default_api_urls"][0].startswith("https://")
    assert seen["url"] == "https://getdcmess.iranlms.ir/"
    assert seen["body"]["method"] == "getDCs" and seen["body"]["api_version"] == "4"
    assert seen["body"]["client"]["app_version"] == "4.4.34"
    assert seen["content_type"] == "application/json"
    assert DcDiscovery.urls_for(payload, DcType.API) == ["https://messengerg2c777.iranlms.ir", "https://messengerg2c888.iranlms.ir"]
    assert DcDiscovery.urls_for(payload, "socket") == ["wss://nsocket10.iranlms.ir:80"]
    run(discovery.close())


def test_dc_discovery_suggested_urls_for_supports_base_info_payload():
    payload = {
        "data": {
            "suggested_urls": {
                "suggested_services": "https://services2.iranlms.ir/",
                "suggested_rubino": "https://rubino2.iranlms.ir",
                "suggested_payment": "https://mmegapal.iranlms.ir",
            }
        }
    }
    assert DcDiscovery.suggested_urls_for(payload, DcType.API) == ["https://services2.iranlms.ir"]
    assert DcDiscovery.suggested_urls_for(payload, DcType.RUBINO) == ["https://rubino2.iranlms.ir"]
    assert DcDiscovery.suggested_urls_for(payload, DcType.WALLET) == ["https://mmegapal.iranlms.ir"]


def test_dc_repository_pools_storages_and_round_trip():
    repo = DcRepository()
    assert repo.api_urls == ["https://messengerg2c1.iranlms.ir"]
    repo.update_from_dcs(DCS_PAYLOAD)
    assert repo.api_urls == ["https://messengerg2c777.iranlms.ir", "https://messengerg2c888.iranlms.ir"]
    assert repo.socket_urls == ["wss://nsocket10.iranlms.ir:80"]
    assert repo.storage_url(2) == "https://messanger2.iranlms.ir/GetFile.ashx"
    assert repo.storage_url("9") is None
    assert repo.cdn_urls_for("PR") == ["https://msgcdn1.iranlms.ir/GetFile"]
    assert repo.pool(DcType.API).get_current() == "https://messengerg2c777.iranlms.ir"
    repo.update_from_base_info({"data": {"suggested_urls": {"suggested_rubino": "https://rubino2.iranlms.ir"}}})
    assert repo.urls(DcType.RUBINO) == ["https://rubino2.iranlms.ir"]
    repo.merge_urls(DcType.SOCKET, ["wss://custom.example:80"])
    assert repo.socket_urls[-1] == "wss://custom.example:80"
    restored = DcRepository.from_dict(repo.to_dict())
    assert restored.storage_url(1) == "https://messanger.iranlms.ir/GetFile.ashx"
    assert restored.suggested_urls == {"suggested_rubino": "https://rubino2.iranlms.ir"}
    assert restored.urls(DcType.DCS) == ["https://getdcmess.iranlms.ir/"]


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------


def test_headers_match_chrome_profile_and_client_hints():
    headers = build_rpc_headers()
    assert headers["user-agent"] == CHROME_USER_AGENT
    assert headers["content-type"] == "text/plain"
    assert headers["origin"] == "https://web.rubika.ir"
    assert headers["referer"] == "https://web.rubika.ir/"
    assert headers["sec-ch-ua-platform"] == '"Windows"'
    assert 'v="145"' in headers["sec-ch-ua"]
    mac = build_client_hints(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )
    assert mac["sec-ch-ua-platform"] == '"macOS"' and 'v="140"' in mac["sec-ch-ua"]
    assert build_websocket_headers()["sec-ch-ua-mobile"] == "?0"


# ---------------------------------------------------------------------------
# Socket transport
# ---------------------------------------------------------------------------


class StubWebSocket:
    def __init__(self, responses):
        self.sent = []
        self.closed = False
        self.responses = list(responses)
        self.wakeup = asyncio.Event()

    async def send(self, payload):
        self.sent.append(payload)
        if payload == "{}" and self.responses and self.responses[0] == "PONG":
            self.responses.pop(0)
            self.responses.insert(0, json.dumps({"status": "OK", "status_det": "OK"}))
            self.wakeup.set()

    async def recv(self):
        while True:
            if self.closed:
                raise ConnectionError("closed")
            if self.responses and self.responses[0] != "PONG":
                return self.responses.pop(0)
            self.wakeup.clear()
            try:
                await asyncio.wait_for(self.wakeup.wait(), timeout=0.05)
            except asyncio.TimeoutError:
                continue

    async def close(self):
        self.closed = True
        self.wakeup.set()


class StubWebSocketsModule:
    def __init__(self, plans):
        self.plans = list(plans)
        self.calls = []
        self.sockets = []

    async def connect(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        plan = self.plans.pop(0) if self.plans else []
        if plan == "FAIL":
            raise OSError("connect failed")
        socket = StubWebSocket(plan)
        self.sockets.append(socket)
        return socket


HANDSHAKE_OK = json.dumps({"status": "OK", "status_det": "OK"})


def test_socket_transport_handshake_headers_and_pong_filtering(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule([[HANDSHAKE_OK, json.dumps({"status": "OK"}), json.dumps({"type": "messenger", "data_enc": "abc"})]])
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))
        transport = SocketTransport(["https://msocket1.iranlms.ir:80/"], heartbeat_interval=60)
        result = await transport.connect("auth-1")
        assert result["status"] == "OK"
        call = module.calls[0]
        assert call["url"] == "wss://msocket1.iranlms.ir:80/"
        assert call["kwargs"]["origin"] == "https://web.rubika.ir"
        assert call["kwargs"]["user_agent_header"] == CHROME_USER_AGENT
        assert call["kwargs"]["additional_headers"]["sec-ch-ua-platform"] == '"Windows"'
        assert "proxy" not in call["kwargs"]
        assert json.loads(module.sockets[0].sent[0]) == {"api_version": "5", "auth": "auth-1", "data": "", "method": "handShake"}
        frame = await transport.recv(timeout=1)
        assert frame == {"type": "messenger", "data_enc": "abc"}
        assert transport.is_connected
        await transport.close()
        assert module.sockets[0].closed
        with pytest.raises(TransportError):
            await transport.recv(timeout=0.1)

    run(scenario())


def test_socket_transport_pings_after_idle_and_reconnects_on_silence(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule(
            [[HANDSHAKE_OK, "PONG"], [HANDSHAKE_OK, json.dumps({"type": "messenger", "data_enc": "after-reconnect"})]]
        )
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))
        transport = SocketTransport(
            ["wss://nsocket10.iranlms.ir:80/", "wss://nsocket11.iranlms.ir:80/"],
            heartbeat_interval=0.05,
            silence_timeout=0.05,
            retry_delay=0.01,
        )
        await transport.connect("auth-1")
        await asyncio.sleep(0.15)
        assert "{}" in module.sockets[0].sent  # ping after idle answered by a pong
        # second ping gets no answer -> silence -> reconnect to the next URL
        await asyncio.sleep(0.4)
        assert len(module.calls) >= 2
        assert module.calls[1]["url"] == "wss://nsocket11.iranlms.ir:80/"
        frame = await transport.recv(timeout=1)
        assert frame["data_enc"] == "after-reconnect"
        await transport.close()

    run(scenario())


def test_socket_transport_tries_next_url_when_connect_fails(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule(["FAIL", [HANDSHAKE_OK]])
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))
        transport = SocketTransport(["wss://a.iranlms.ir:80", "wss://b.iranlms.ir:80"], heartbeat_interval=60)
        await transport.connect("auth-1")
        assert [c["url"] for c in module.calls] == ["wss://a.iranlms.ir:80", "wss://b.iranlms.ir:80"]
        assert transport.connected_url == "wss://b.iranlms.ir:80"
        await transport.close()

        failing = StubWebSocketsModule(["FAIL", "FAIL"])
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: failing))
        transport = SocketTransport(["wss://a.iranlms.ir:80", "wss://b.iranlms.ir:80"], heartbeat_interval=60)
        with pytest.raises(NetworkError):
            await transport.connect("auth-1")

    run(scenario())


def test_socket_transport_raises_mapped_rpc_error_on_bad_handshake(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule([[json.dumps({"status": "ERROR_ACTION", "status_det": "INVALID_AUTH"})]])
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))
        transport = SocketTransport(["wss://a.iranlms.ir:80"], heartbeat_interval=60)
        with pytest.raises(InvalidAuth):
            await transport.connect("auth-1")
        assert module.sockets[0].closed

    run(scenario())


def test_socket_transport_refuses_proxy_without_support(monkeypatch):
    class NoProxyModule:
        @staticmethod
        async def connect(url, *, origin=None, user_agent_header=None, open_timeout=None, close_timeout=None, additional_headers=None):
            raise AssertionError("must not connect")

    async def scenario():
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: NoProxyModule))
        transport = SocketTransport(["wss://a.iranlms.ir:80"], proxy="socks5://127.0.0.1:1080")
        with pytest.raises(NetworkError) as excinfo:
            await transport.connect("auth-1")
        assert "proxy" in str(excinfo.value)

    run(scenario())


# ---------------------------------------------------------------------------
# Upload / download
# ---------------------------------------------------------------------------


def test_upload_transport_streams_parts_with_headers_and_progress(tmp_path):
    source = tmp_path / "sample.bin"
    source.write_bytes(b"abcdefgh")
    parts = []
    progress = []

    async def handler(request: httpx.Request) -> httpx.Response:
        parts.append(
            {k: request.headers[k] for k in ("auth", "file-id", "access-hash-send", "part-number", "total-part", "chunk-size")}
            | {"body": request.content}
        )
        if request.headers["part-number"] == "1":
            return httpx.Response(200, json={"status": "OK", "status_det": "OK", "data": {}})
        return httpx.Response(200, json={"status": "OK", "status_det": "OK", "data": {"access_hash_rec": "rec-1"}})

    transport = UploadTransport(chunk_size=3)
    transport.use_client(_mock_client(handler))
    descriptor = UploadDescriptor(id="f1", dc_id="5", access_hash_send="send-1", upload_url="https://up.iranlms.ir/UploadFile.ashx")

    async def on_progress(current, total, label):
        progress.append((current, total, label))

    result = run(transport.upload_file(auth="auth-1", descriptor=descriptor, path=source, progress=on_progress, progress_args=("tag",)))
    assert result.access_hash_rec == "rec-1"
    assert [p["part-number"] for p in parts] == ["1", "2", "3"]
    assert parts[0]["total-part"] == "3" and parts[0]["chunk-size"] == "3" and parts[2]["chunk-size"] == "2"
    assert parts[0]["auth"] == "auth-1" and parts[0]["file-id"] == "f1" and parts[0]["access-hash-send"] == "send-1"
    assert b"".join(p["body"] for p in parts) == b"abcdefgh"
    assert progress == [(3, 8, "tag"), (6, 8, "tag"), (8, 8, "tag")]


def test_upload_transport_retries_part_on_5xx():
    responses = [
        httpx.Response(500, text="oops"),
        httpx.Response(200, json={"status": "OK", "status_det": "OK", "data": {"access_hash_rec": "rec"}}),
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    transport = UploadTransport(chunk_size=10, retry_policy=no_sleep(RetryPolicy()))
    transport.use_client(_mock_client(handler))
    descriptor = UploadDescriptor(id="f1", dc_id="5", access_hash_send="s", upload_url="https://up.iranlms.ir/")
    result = run(transport.upload_file(auth="a", descriptor=descriptor, data=b"12345"))
    assert result.access_hash_rec == "rec"


def test_download_transport_uses_storage_url_ranges_and_total_length(tmp_path):
    content = b"0123456789abcdef"
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        start = int(request.headers["start-index"])
        end = int(request.headers["last-index"])
        requests.append(
            (str(request.url), request.headers["auth"], request.headers["file-id"], request.headers["access-hash-rec"], start, end)
        )
        return httpx.Response(200, content=content[start : end + 1], headers={"total_length": str(len(content))})

    transport = DownloadTransport(chunk_size=6)
    transport.use_client(_mock_client(handler))
    target = tmp_path / "out.bin"
    progress = []
    result = run(
        transport.download_file(
            auth="auth-1",
            file_id="f1",
            access_hash_rec="rec-1",
            url="https://messanger2.iranlms.ir/GetFile.ashx",
            path=target,
            progress=lambda current, total: progress.append((current, total)),
        )
    )
    assert result == target and target.read_bytes() == content
    assert requests[0][:4] == ("https://messanger2.iranlms.ir/GetFile.ashx", "auth-1", "f1", "rec-1")
    assert [(r[4], r[5]) for r in requests] == [(0, 5), (6, 11), (12, 15)]
    assert progress == [(6, 16), (12, 16), (16, 16)]
    memory = run(transport.download_file(auth="a", file_id="f1", access_hash_rec="r", dc_id=2, in_memory=True))
    assert memory == content


def test_download_transport_streams_direct_url_in_memory():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, content=b"abcdef", headers={"content-length": "6"})

    transport = DownloadTransport(chunk_size=3)
    transport.use_client(_mock_client(handler))
    assert run(transport.download_url(url="https://rubino2.iranlms.ir/video/file-1", in_memory=True)) == b"abcdef"


# ---------------------------------------------------------------------------
# Bot API transport
# ---------------------------------------------------------------------------


def test_bot_transport_builds_url_unwraps_and_raises():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://botapi.rubika.ir/v3/TOKEN/getMe"
        assert json.loads(request.content) == {}
        return httpx.Response(200, json={"status": "OK", "data": {"bot": {"bot_id": "b1"}}})

    transport = BotTransport("TOKEN")
    transport.use_client(_mock_client(handler))
    assert run(transport.call("getMe")) == {"bot": {"bot_id": "b1"}}
    assert transport.build_method_url("sendMessage").endswith("/TOKEN/sendMessage")
    assert BotTransport.unwrap({"ok": True, "result": {"message_id": "1"}}) == {"message_id": "1"}
    with pytest.raises(InvalidAuth):
        BotTransport.unwrap({"status": "ERROR_GENERIC", "status_det": "INVALID_AUTH"})
    from rubigram.errors import BotApiError

    with pytest.raises(BotApiError):
        BotTransport.unwrap({"ok": False, "description": "bad", "error_code": 400})
