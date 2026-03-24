from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any, Optional, Sequence
from urllib.parse import urlparse, urlunparse

from rubigram.exceptions import NetworkError, RubikaError, TransportError, map_rpc_error
from rubigram.network.headers import CHROME_USER_AGENT, WEB_ORIGIN, build_websocket_headers

log = logging.getLogger(__name__)


class SocketTransport:
    DEFAULT_TIMEOUT = 20.0
    DEFAULT_HEARTBEAT_INTERVAL = 30.0
    ORIGIN = WEB_ORIGIN
    USER_AGENT = CHROME_USER_AGENT

    def __init__(
        self,
        urls: Sequence[str],
        timeout: float = DEFAULT_TIMEOUT,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
    ):
        self._urls = [self._normalize_url(url) for url in urls if url]
        self._timeout = timeout
        self._heartbeat_interval = heartbeat_interval
        self._websocket: Any = None
        self._connected_url: Optional[str] = None
        self._last_auth: Optional[str] = None
        self._heartbeat_task: Optional[asyncio.Task[None]] = None
        self._reader_task: Optional[asyncio.Task[None]] = None
        self._incoming_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._disconnect_marker = {"_socket_disconnected": True}

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme in {"ws", "wss"}:
            return url
        if parsed.scheme == "http":
            return urlunparse(parsed._replace(scheme="ws"))
        if parsed.scheme == "https":
            return urlunparse(parsed._replace(scheme="wss"))
        if not parsed.scheme:
            return f"wss://{url}"
        return url

    @staticmethod
    def _load_websockets_module():
        try:
            import websockets
        except ImportError as e:
            raise TransportError(
                "Socket handshake requires the 'websockets' package. Install it with: pip install websockets"
            ) from e
        return websockets

    async def handshake(
        self,
        auth: str,
        api_version: str = "5",
        force_reconnect: bool = False,
    ) -> dict[str, Any]:
        if not auth:
            raise TransportError("Socket handshake requires auth")
        if not self._urls:
            raise TransportError("No socket URLs configured for handshake")
        if (
            self._websocket is not None
            and not force_reconnect
            and self._last_auth == auth
            and self._heartbeat_task is not None
            and not self._heartbeat_task.done()
        ):
            return {"status": "OK", "status_det": "OK"}

        if self._websocket is not None:
            await self.close()

        websockets = self._load_websockets_module()
        last_error: Optional[Exception] = None

        for url in self._urls:
            websocket = None
            try:
                websocket = await websockets.connect(
                    url,
                    origin=self.ORIGIN,
                    user_agent_header=self.USER_AGENT,
                    open_timeout=self._timeout,
                    close_timeout=self._timeout,
                )
                payload = {
                    "api_version": api_version,
                    "auth": auth,
                    "data": "",
                    "method": "handShake",
                }
                await websocket.send(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
                raw_response = await asyncio.wait_for(websocket.recv(), timeout=self._timeout)

                if isinstance(raw_response, bytes):
                    raw_response = raw_response.decode("utf-8")

                response = json.loads(raw_response)
                status = response.get("status")
                if status and status != "OK":
                    raise map_rpc_error(status, response.get("status_det"), response)

                self._cancel_heartbeat()
                self._cancel_reader()
                self._websocket = websocket
                self._connected_url = url
                self._last_auth = auth
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="rubigram-socket-heartbeat")
                self._reader_task = asyncio.create_task(self._reader_loop(), name="rubigram-socket-reader")
                return response
            except Exception as e:
                last_error = e
                if websocket is not None and websocket is not self._websocket:
                    try:
                        await websocket.close()
                    except Exception:
                        pass

        if isinstance(last_error, (RubikaError, TransportError)):
            raise last_error
        if last_error is not None:
            raise NetworkError(
                f"Socket handshake failed for all configured URLs: {type(last_error).__name__}: {last_error}",
                last_error,
            ) from last_error
        raise TransportError("Socket handshake failed unexpectedly")

    async def _heartbeat_loop(self) -> None:
        while self._websocket is not None:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                websocket = self._websocket
                if websocket is None:
                    return

                await websocket.send("{}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Socket heartbeat failed for %s: %s", self._connected_url, e)
                await self._drop_connection()
                return

    def _cancel_heartbeat(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    def _cancel_reader(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None

    async def _reader_loop(self) -> None:
        while self._websocket is not None:
            try:
                raw_response = await self._websocket.recv()
                if isinstance(raw_response, bytes):
                    raw_response = raw_response.decode("utf-8")

                response = json.loads(raw_response)
                await self._incoming_queue.put(response)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Socket reader failed for %s: %s", self._connected_url, e)
                await self._drop_connection()
                return

    async def recv(self, timeout: Optional[float] = None) -> dict[str, Any]:
        if self._websocket is None:
            raise TransportError("Socket connection is not active")

        if timeout is None:
            payload = await self._incoming_queue.get()
        else:
            payload = await asyncio.wait_for(self._incoming_queue.get(), timeout=timeout)

        if payload.get("_socket_disconnected"):
            raise TransportError("Socket connection dropped")
        return payload

    async def _drop_connection(self) -> None:
        websocket = self._websocket
        self._websocket = None
        self._connected_url = None
        self._last_auth = None

        task = self._heartbeat_task
        self._heartbeat_task = None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        reader_task = self._reader_task
        self._reader_task = None
        if reader_task is not None and reader_task is not asyncio.current_task():
            reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader_task

        old_queue = self._incoming_queue
        self._incoming_queue = asyncio.Queue()
        with contextlib.suppress(asyncio.QueueFull):
            old_queue.put_nowait(self._disconnect_marker)

        if websocket is not None:
            with contextlib.suppress(Exception):
                await websocket.close()

    async def close(self) -> None:
        await self._drop_connection()
