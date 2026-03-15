import asyncio

import httpx

from rubigram.network.discovery import DcDiscovery
from rubigram.network.transport import ApiUrlPool, RpcTransport


class StubAsyncClient:
    def __init__(self, actions):
        self.actions = list(actions)
        self.calls = []

    async def post(self, url, content=None, json=None):
        self.calls.append({"url": url, "content": content, "json": json})
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action
        return action

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
