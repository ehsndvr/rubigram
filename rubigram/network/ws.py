"""WebSocket transport for pushed updates.

Behaviour copied from web.rubika.ir 4.4.34:

- connect to a socket URL, send ``{"api_version": "5", "auth": …, "data": "", "method": "handShake"}``;
- every received frame resets the timers; 30 s after the last frame the
  literal ``{}`` ping is sent; if nothing arrives within 20 s after a ping the
  connection is considered dead;
- after a drop the transport waits 5 s (growing to 60 s on repeated failures),
  rotates to the next socket URL, reconnects and handshakes again;
- ``{"type": "messenger", "data_enc": …}`` frames carry updates; frames without
  ``type`` are pongs.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Sequence
from urllib.parse import urlparse, urlunparse

from rubigram.errors import NetworkError, RpcError, TransportError, map_rpc_error
from rubigram.network.headers import CHROME_USER_AGENT, WEB_ORIGIN, build_websocket_headers
from rubigram.network.pool import UrlPool

log = logging.getLogger(__name__)

FrameCallback = Callable[[Dict[str, Any]], "Awaitable[None] | None"]


class SocketTransport:
    """Persistent connection to a Rubika socket DC with automatic recovery."""

    DEFAULT_TIMEOUT = 20.0
    DEFAULT_PING_DELAY = 30.0
    DEFAULT_SILENCE_TIMEOUT = 20.0
    DEFAULT_RETRY_DELAY = 5.0
    MAX_RETRY_DELAY = 60.0
    HANDSHAKE_API_VERSION = "5"
    ORIGIN = WEB_ORIGIN
    USER_AGENT = CHROME_USER_AGENT

    def __init__(
        self,
        urls: "Sequence[str] | UrlPool",
        timeout: float = DEFAULT_TIMEOUT,
        heartbeat_interval: float = DEFAULT_PING_DELAY,
        *,
        silence_timeout: float = DEFAULT_SILENCE_TIMEOUT,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        api_version: str = HANDSHAKE_API_VERSION,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        origin: Optional[str] = None,
        on_frame: Optional[FrameCallback] = None,
        auto_reconnect: bool = True,
    ):
        if isinstance(urls, UrlPool):
            self._pool = urls
        else:
            self._pool = UrlPool([self._normalize_url(url) for url in urls if url])
        self._timeout = timeout
        self._ping_delay = heartbeat_interval
        self._silence_timeout = silence_timeout
        self._retry_delay = retry_delay
        self._api_version = api_version
        self._proxy = proxy
        self._user_agent = user_agent or self.USER_AGENT
        self._origin = origin or self.ORIGIN
        self._on_frame = on_frame
        self._auto_reconnect = auto_reconnect

        self._websocket: Any = None
        self._connected_url: Optional[str] = None
        self._auth: Optional[str] = None
        self._reader_task: Optional[asyncio.Task[None]] = None
        self._keepalive_task: Optional[asyncio.Task[None]] = None
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        self._incoming: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._last_frame_at = 0.0
        self._ping_sent_at: Optional[float] = None
        self._closed = True
        self._failures = 0
        self._connect_lock = asyncio.Lock()
        self._disconnect_marker: Dict[str, Any] = {"_socket_disconnected": True}
        self._connected_event = asyncio.Event()

    # -- helpers ----------------------------------------------------------

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
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise TransportError("The socket transport requires the 'websockets' package") from exc
        return websockets

    def _connect_kwargs(self, websockets_module: Any) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "origin": self._origin,
            "user_agent_header": self._user_agent,
            "open_timeout": self._timeout,
            "close_timeout": self._timeout,
            "additional_headers": build_websocket_headers(self._user_agent),
        }
        try:
            params = inspect.signature(websockets_module.connect).parameters
        except (TypeError, ValueError):  # pragma: no cover - exotic stubs
            params = {}
        if params and "additional_headers" not in params and "extra_headers" in params:
            kwargs["extra_headers"] = kwargs.pop("additional_headers")
        if self._proxy:
            if params and "proxy" not in params:
                raise TransportError(
                    "The installed websockets version has no proxy support (15+ required); "
                    "refusing to open the socket without the configured proxy"
                )
            kwargs["proxy"] = self._proxy
        return kwargs

    @property
    def is_connected(self) -> bool:
        return self._websocket is not None and not self._closed

    @property
    def connected_url(self) -> Optional[str]:
        return self._connected_url

    @property
    def urls(self) -> list[str]:
        return self._pool.urls

    def replace_urls(self, urls: Sequence[str]) -> None:
        self._pool.replace([self._normalize_url(url) for url in urls if url], strict=False)

    # -- connection lifecycle --------------------------------------------

    async def connect(self, auth: str, *, force_reconnect: bool = False) -> Dict[str, Any]:
        """Open the socket (or reuse it) and perform the handshake.

        Returns the handshake response.  Raises :class:`TransportError` when no
        URL is configured and :class:`NetworkError` when every URL failed.
        """
        if not auth:
            raise TransportError("Socket handshake requires auth")
        if self._pool.count == 0:
            raise TransportError("No socket URLs configured")
        async with self._connect_lock:
            if self.is_connected and not force_reconnect and self._auth == auth:
                return {"status": "OK", "status_det": "OK"}
            await self._teardown(cancel_reconnect=True)
            self._auth = auth
            response = await self._connect_any()
            self._closed = False
            self._failures = 0
            self._start_tasks()
            self._connected_event.set()
            return response

    async def handshake(self, auth: str, api_version: Optional[str] = None, force_reconnect: bool = False) -> Dict[str, Any]:
        """Old name of :meth:`connect`."""
        if api_version:
            self._api_version = api_version
        return await self.connect(auth, force_reconnect=force_reconnect)

    async def _connect_any(self) -> Dict[str, Any]:
        websockets_module = self._load_websockets_module()
        last_error: Optional[BaseException] = None
        for _ in range(max(1, self._pool.count)):
            url = self._pool.get_current()
            try:
                return await self._connect_once(websockets_module, url)
            except RpcError:
                raise
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - try the next DC
                last_error = exc
                log.warning("Socket connect to %s failed: %s", url, exc)
                self._pool.force_rotate()
        raise NetworkError(
            f"Socket handshake failed for all configured URLs: {type(last_error).__name__}: {last_error}",
            last_error,
        )

    async def _connect_once(self, websockets_module: Any, url: str) -> Dict[str, Any]:
        websocket = await websockets_module.connect(url, **self._connect_kwargs(websockets_module))
        try:
            payload = {
                "api_version": self._api_version,
                "auth": self._auth,
                "data": "",
                "method": "handShake",
            }
            await websocket.send(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
            raw_response = await asyncio.wait_for(websocket.recv(), timeout=self._timeout)
            response = self._decode(raw_response)
            status = response.get("status")
            if status and status != "OK":
                raise map_rpc_error(str(status), response.get("status_det"), response, method="handShake")
        except BaseException:
            with contextlib.suppress(Exception):
                await websocket.close()
            raise
        self._websocket = websocket
        self._connected_url = url
        self._last_frame_at = time.monotonic()
        self._ping_sent_at = None
        return response

    @staticmethod
    def _decode(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise TransportError(f"Unexpected socket frame: {type(data).__name__}")
        return data

    def _start_tasks(self) -> None:
        self._reader_task = asyncio.create_task(self._reader_loop(), name="rubigram-socket-reader")
        self._keepalive_task = asyncio.create_task(self._keepalive_loop(), name="rubigram-socket-keepalive")

    async def _reader_loop(self) -> None:
        websocket = self._websocket
        try:
            while websocket is not None and websocket is self._websocket:
                raw = await websocket.recv()
                frame = self._decode(raw)
                self._last_frame_at = time.monotonic()
                self._ping_sent_at = None
                if "type" not in frame and "data_enc" not in frame:
                    # Pong or bare status frame: keeps the connection alive, nothing to deliver.
                    continue
                await self._incoming.put(frame)
                if self._on_frame is not None:
                    try:
                        result = self._on_frame(frame)
                        if inspect.isawaitable(result):
                            await result
                    except Exception:  # noqa: BLE001 - a bad callback must not kill the reader
                        log.exception("Socket frame callback failed")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            if not self._closed:
                log.warning("Socket reader stopped for %s: %s", self._connected_url, exc)
                self._schedule_reconnect("reader error")

    async def _keepalive_loop(self) -> None:
        try:
            while not self._closed:
                now = time.monotonic()
                if self._ping_sent_at is not None:
                    deadline = self._ping_sent_at + self._silence_timeout
                    if now >= deadline:
                        log.warning("Socket %s silent for %.0fs after ping; reconnecting", self._connected_url, self._silence_timeout)
                        self._schedule_reconnect("silence")
                        return
                    await asyncio.sleep(min(deadline - now, 1.0))
                    continue
                due = self._last_frame_at + self._ping_delay
                if now >= due:
                    await self.send({})
                    self._ping_sent_at = time.monotonic()
                    continue
                await asyncio.sleep(min(due - now, 1.0))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            if not self._closed:
                log.warning("Socket keepalive failed for %s: %s", self._connected_url, exc)
                self._schedule_reconnect("keepalive error")

    def _schedule_reconnect(self, reason: str) -> None:
        if self._closed or not self._auto_reconnect:
            self._mark_dropped()
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect(reason), name="rubigram-socket-reconnect")

    def _mark_dropped(self) -> None:
        self._connected_event.clear()
        with contextlib.suppress(asyncio.QueueFull):
            self._incoming.put_nowait(dict(self._disconnect_marker))

    async def _reconnect(self, reason: str) -> None:
        auth = self._auth
        await self._drop_socket()
        self._connected_event.clear()
        while not self._closed and auth:
            self._failures += 1
            delay = min(self._retry_delay * (2 ** max(0, self._failures - 2)), self.MAX_RETRY_DELAY) if self._failures > 1 else self._retry_delay
            log.info("Socket reconnect (%s) in %.0fs, attempt %d", reason, delay, self._failures)
            await asyncio.sleep(delay)
            if self._closed:
                return
            self._pool.force_rotate()
            try:
                await self._connect_any()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("Socket reconnect attempt %d failed: %s", self._failures, exc)
                continue
            self._failures = 0
            self._start_tasks()
            self._connected_event.set()
            log.info("Socket reconnected to %s", self._connected_url)
            return

    async def wait_connected(self, timeout: Optional[float] = None) -> None:
        """Block until the socket is (re)connected."""
        if timeout is None:
            await self._connected_event.wait()
        else:
            await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)

    # -- I/O --------------------------------------------------------------

    async def send(self, payload: Dict[str, Any]) -> None:
        websocket = self._websocket
        if websocket is None:
            raise TransportError("Socket connection is not active")
        await websocket.send(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))

    async def recv(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Next update-carrying frame (``type: messenger``); pongs are filtered out."""
        if self._closed and self._incoming.empty():
            raise TransportError("Socket connection is not active")
        if timeout is None:
            frame = await self._incoming.get()
        else:
            frame = await asyncio.wait_for(self._incoming.get(), timeout=timeout)
        if frame.get("_socket_disconnected"):
            raise TransportError("Socket connection dropped")
        return frame

    async def _drop_socket(self) -> None:
        websocket = self._websocket
        self._websocket = None
        self._connected_url = None
        for attr in ("_reader_task", "_keepalive_task"):
            task = getattr(self, attr)
            setattr(self, attr, None)
            if task is not None and task is not asyncio.current_task():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        if websocket is not None:
            with contextlib.suppress(Exception):
                await websocket.close()

    async def _teardown(self, *, cancel_reconnect: bool) -> None:
        if cancel_reconnect:
            task = self._reconnect_task
            self._reconnect_task = None
            if task is not None and task is not asyncio.current_task():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        await self._drop_socket()

    async def close(self) -> None:
        """Close the connection and stop every background task."""
        self._closed = True
        await self._teardown(cancel_reconnect=True)
        self._connected_event.clear()
        self._mark_dropped()

    # Old names kept for callers of the previous implementation.
    async def _drop_connection(self) -> None:
        await self._drop_socket()
        self._mark_dropped()


__all__ = ["SocketTransport", "FrameCallback"]
