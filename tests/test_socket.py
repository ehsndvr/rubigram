import asyncio
import json

from rubigram.network.headers import CHROME_USER_AGENT
from rubigram.network.socket import SocketTransport


class StubWebSocket:
    def __init__(self, responses=None):
        self.sent = []
        self.closed = False
        self.responses = list(responses or [json.dumps({"status": "OK", "status_det": "OK"})])

    async def send(self, payload):
        self.sent.append(payload)

    async def recv(self):
        await asyncio.sleep(0)
        if self.responses:
            return self.responses.pop(0)
        return json.dumps({"status": "OK", "status_det": "OK"})

    async def close(self):
        self.closed = True


class StubWebSocketsModule:
    def __init__(self, responses=None):
        self.calls = []
        self.websocket = StubWebSocket(responses=responses)

    async def connect(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        return self.websocket


def test_socket_transport_disables_proxy_and_sends_browserish_headers(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule()
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))

        transport = SocketTransport(["https://msocket1.iranlms.ir:80/"], heartbeat_interval=60)
        result = await transport.handshake("auth-1")

        assert result["status"] == "OK"
        assert module.calls[0]["url"] == "wss://msocket1.iranlms.ir:80/"
        assert module.calls[0]["kwargs"]["proxy"] is None
        assert module.calls[0]["kwargs"]["origin"] == "https://web.rubika.ir"
        assert module.calls[0]["kwargs"]["user_agent_header"] == CHROME_USER_AGENT
        assert module.calls[0]["kwargs"]["additional_headers"]["sec-ch-ua-platform"] == '"Windows"'
        assert module.calls[0]["kwargs"]["additional_headers"]["referer"] == "https://web.rubika.ir/"
        assert json.loads(module.websocket.sent[0]) == {
            "api_version": "5",
            "auth": "auth-1",
            "data": "",
            "method": "handShake",
        }
        assert module.websocket.closed is False

        await transport.close()
        assert module.websocket.closed is True

    asyncio.run(scenario())


def test_socket_transport_sends_periodic_empty_heartbeat(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule(
            responses=[
                json.dumps({"status": "OK", "status_det": "OK"}),
                json.dumps({"status": "OK", "status_det": "OK"}),
            ]
        )
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))

        transport = SocketTransport(["wss://nsocket10.iranlms.ir:80/"], heartbeat_interval=0.01)
        await transport.handshake("auth-1")
        await asyncio.sleep(0.03)

        assert "{}" in module.websocket.sent

        await transport.close()

    asyncio.run(scenario())


def test_socket_transport_queues_incoming_messages(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule(
            responses=[
                json.dumps({"status": "OK", "status_det": "OK"}),
                json.dumps({"type": "messenger", "data_enc": "abc"}),
            ]
        )
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))

        transport = SocketTransport(["wss://nsocket10.iranlms.ir:80/"], heartbeat_interval=60)
        await transport.handshake("auth-1")
        payload = await transport.recv(timeout=0.1)

        assert payload == {"type": "messenger", "data_enc": "abc"}

        await transport.close()

    asyncio.run(scenario())



def test_socket_transport_recv_raises_when_connection_drops(monkeypatch):
    async def scenario():
        module = StubWebSocketsModule(
            responses=[
                json.dumps({"status": "OK", "status_det": "OK"}),
            ]
        )
        monkeypatch.setattr(SocketTransport, "_load_websockets_module", staticmethod(lambda: module))

        transport = SocketTransport(["wss://nsocket10.iranlms.ir:80/"], heartbeat_interval=60)
        await transport.handshake("auth-1")
        transport._cancel_reader()
        transport._incoming_queue = asyncio.Queue()

        waiter = asyncio.create_task(transport.recv())
        await asyncio.sleep(0)
        await transport._drop_connection()

        try:
            await waiter
        except Exception as exc:
            assert str(exc) == "Socket connection dropped"
        else:
            raise AssertionError("Expected recv to fail after drop")

    asyncio.run(scenario())
