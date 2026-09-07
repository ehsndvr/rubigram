import asyncio
from pathlib import Path

import httpx

from rubigram.enums import DcType
from rubigram.network.discovery import DcDiscovery
from rubigram.network.transport import ApiUrlPool, JsonTransport, RpcTransport
from rubigram.network.download import DownloadTransport
from rubigram.network.upload import UploadTransport
from rubigram.types import UploadDescriptor


class StubAsyncClient:
    def __init__(self, actions):
        self.actions = list(actions)
        self.calls = []

    async def post(self, url, content=None, json=None, headers=None):
        self.calls.append({"url": url, "content": content, "json": json, "headers": headers})
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action
        return action

    def stream(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action

        class _StreamContext:
            def __init__(self, response):
                self._response = response

            async def __aenter__(self):
                async def _aiter_bytes(chunk_size):
                    content = self._response.content
                    for index in range(0, len(content), chunk_size):
                        yield content[index:index + chunk_size]

                setattr(self._response, "aiter_bytes", _aiter_bytes)
                return self._response

            async def __aexit__(self, exc_type, exc, tb):
                return None

        return _StreamContext(action)

    async def aclose(self):
        return None

    def close(self):
        return None


def _response(status_code=200, json_body=None, text=""):
    request = httpx.Request("POST", "https://example.invalid/")
    if json_body is not None:
        return httpx.Response(status_code, request=request, json=json_body)
    return httpx.Response(status_code, request=request, text=text)


def test_transport_failover_and_text_plain_body():
    async def scenario():
        pool = ApiUrlPool(
            [
                "https://messengerg2c513.iranlms.ir",
                "https://messengerg2c466.iranlms.ir",
            ]
        )
        transport = RpcTransport(DcDiscovery(), pool)
        transport._client = StubAsyncClient(
            [
                httpx.ConnectError("boom"),
                _response(200, {"status": "OK", "status_det": "OK"}),
            ]
        )

        result = await transport.send_payload({"api_version": "6", "auth": "", "data_enc": "abc", "sign": "sig"})

        assert result["status"] == "OK"
        assert pool.get_current() == "https://messengerg2c466.iranlms.ir"
        assert isinstance(transport._client.calls[0]["content"], str)

        await transport.close()

    asyncio.run(scenario())



def test_transport_refreshes_pool_after_502():
    async def scenario():
        class StubDiscovery:
            async def fetch_dcs(self):
                return {
                    "data": {
                        "default_api_urls": [
                            "https://messengerg2c777.iranlms.ir",
                            "https://messengerg2c888.iranlms.ir",
                        ]
                    }
                }

            @staticmethod
            def urls_for(payload, dc_type):
                return DcDiscovery.urls_for(payload, dc_type)

        pool = ApiUrlPool(["https://messengerg2c597.iranlms.ir"])
        transport = RpcTransport(StubDiscovery(), pool)
        transport._client = StubAsyncClient(
            [
                _response(502, text="bad gateway"),
                _response(200, {"status": "OK", "status_det": "OK"}),
            ]
        )

        result = await transport.send_payload({"api_version": "6", "auth": "", "data_enc": "abc", "sign": "sig"})

        assert result["status"] == "OK"
        assert transport._client.calls[0]["url"] == "https://messengerg2c597.iranlms.ir/"
        assert transport._client.calls[1]["url"] == "https://messengerg2c777.iranlms.ir/"
        assert pool.get_current() == "https://messengerg2c777.iranlms.ir"

        await transport.close()

    asyncio.run(scenario())



def test_download_transport_downloads_chunked_file():
    async def scenario():
        transport = DownloadTransport(chunk_size=3)
        transport._client = StubAsyncClient([
            _response(200, text="abcd"),
            _response(200, text="ef"),
        ])

        target = Path.cwd() / "_download_transport_voice.ogg"
        result = await transport.download_file(
            auth="auth123",
            file_id="10",
            dc_id="488",
            access_hash_rec="hash-rec",
            file_size=6,
            path=target,
        )

        assert result == target
        assert target.read_bytes() == b"abcdef"
        target.unlink(missing_ok=True)
        assert transport._client.calls[0]["url"] == "https://messenger488.iranlms.ir/GetFile.ashx"

        await transport.close()

    asyncio.run(scenario())



def test_upload_transport_reports_progress():
    async def scenario():
        transport = UploadTransport(chunk_size=3)
        transport._client = StubAsyncClient([
            _response(200, {"status": "OK", "status_det": "OK", "data": {}}),
            _response(200, {"status": "OK", "status_det": "OK", "data": {"access_hash_rec": "rec"}}),
        ])

        target = Path.cwd() / "_upload_transport_voice.ogg"
        target.write_bytes(b"abcdef")
        progress_calls = []

        def progress(current, total, label):
            progress_calls.append((current, total, label))

        result = await transport.upload_file(
            auth="auth123",
            descriptor=UploadDescriptor(id="10", dc_id="488", access_hash_send="send-hash", upload_url="https://upmessenger488.iranlms.ir/UploadFile.ashx"),
            path=target,
            progress=progress,
            progress_args=("upload",),
        )

        assert result.access_hash_rec == "rec"
        assert progress_calls == [(3, 6, "upload"), (6, 6, "upload")]

        target.unlink(missing_ok=True)
        await transport.close()

    asyncio.run(scenario())


def test_dc_discovery_urls_for_supports_typed_dc_kinds():
    payload = {
        "data": {
            "default_api_urls": [
                "https://messengerg2c777.iranlms.ir",
                "messengerg2c888.iranlms.ir",
            ],
            "default_sockets": [
                "wss://nsocket10.iranlms.ir:80/",
            ],
            "storages": {
                DcType.RUBINO.value: [
                    "https://rubino16.iranlms.ir",
                    "rubino20.iranlms.ir",
                ],
                DcType.WALLET.value: ["wallet42.iranlms.ir"],
            },
        }
    }

    assert DcDiscovery.urls_for(payload, DcType.API) == [
        "https://messengerg2c777.iranlms.ir",
        "https://messengerg2c888.iranlms.ir",
    ]
    assert DcDiscovery.urls_for(payload, DcType.SOCKET) == [
        "https://nsocket10.iranlms.ir:80",
    ]
    assert DcDiscovery.urls_for(payload, DcType.RUBINO) == [
        "https://rubino16.iranlms.ir",
        "https://rubino20.iranlms.ir",
    ]
    assert DcDiscovery.urls_for(payload, DcType.WALLET) == [
        "https://wallet42.iranlms.ir",
    ]


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

    assert DcDiscovery.suggested_urls_for(payload, DcType.API) == [
        "https://services2.iranlms.ir",
    ]
    assert DcDiscovery.suggested_urls_for(payload, DcType.RUBINO) == [
        "https://rubino2.iranlms.ir",
    ]
    assert DcDiscovery.suggested_urls_for(payload, DcType.WALLET) == [
        "https://mmegapal.iranlms.ir",
    ]


def test_json_transport_failover_uses_json_body():
    async def scenario():
        transport = JsonTransport(
            [
                "https://rubino16.iranlms.ir",
                "https://rubino20.iranlms.ir",
            ]
        )
        transport._client = StubAsyncClient(
            [
                httpx.ConnectError("boom"),
                _response(200, {"status": "OK", "status_det": "OK", "data": {"posts": []}}),
            ]
        )

        result = await transport.send_json({"method": "getProfilePosts"})

        assert result["status"] == "OK"
        assert transport._client.calls[0]["url"] == "https://rubino16.iranlms.ir/"
        assert transport._client.calls[1]["url"] == "https://rubino20.iranlms.ir/"
        assert transport._client.calls[0]["json"] == {"method": "getProfilePosts"}

        await transport.close()

    asyncio.run(scenario())



def test_download_transport_reports_progress():
    async def scenario():
        transport = DownloadTransport(chunk_size=3)
        transport._client = StubAsyncClient([
            _response(200, text="abcd"),
            _response(200, text="ef"),
        ])
        progress_calls = []

        def progress(current, total, label):
            progress_calls.append((current, total, label))

        result = await transport.download_file(
            auth="auth123",
            file_id="10",
            dc_id="488",
            access_hash_rec="hash-rec",
            file_size=6,
            in_memory=True,
            progress=progress,
            progress_args=("download",),
        )

        assert result == b"abcdef"
        assert progress_calls == [(4, 6, "download"), (6, 6, "download")]

        await transport.close()

    asyncio.run(scenario())


def test_download_transport_downloads_direct_url():
    async def scenario():
        transport = DownloadTransport(chunk_size=3)
        transport._client = StubAsyncClient([
            _response(200, text="abcdef"),
        ])

        result = await transport.download_url(
            url="https://rubino2.iranlms.ir/video/file-1",
            in_memory=True,
        )

        assert result == b"abcdef"
        assert transport._client.calls[0]["url"] == "https://rubino2.iranlms.ir/video/file-1"

        await transport.close()

    asyncio.run(scenario())
