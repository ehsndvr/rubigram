"""Receiving updates: socket pushes (``Transport.WS``) or polling (``Transport.HTTP``)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Dict, Optional

from rubigram.client.base import BaseClient
from rubigram.errors import DecodeError, LoginRequired, NetworkError, RubigramError, TransportError
from rubigram.network import SocketTransport, Transport
from rubigram.raw.methods import GetChatsUpdates, GetMessagesUpdates
from rubigram.types import ChatsUpdates, MessagesUpdates, MessageUpdate, Updates

log = logging.getLogger(__name__)


class UpdatesMixin(BaseClient):
    # -- socket ---------------------------------------------------------------

    async def _ensure_socket(self, force_reconnect: bool = False) -> None:
        if not self.enable_socket or self.is_bot:
            return
        auth = await self.storage.auth()
        if not auth:
            return
        if self._socket is None:
            self._socket = SocketTransport(
                self.dc.pool("socket"),
                timeout=self.timeout,
                heartbeat_interval=self.socket_heartbeat_interval,
                api_version=self.SOCKET_HANDSHAKE_API_VERSION,
                proxy=self.proxy,
                user_agent=self.user_agent,
            )
        await self._socket.connect(auth, force_reconnect=force_reconnect)

    async def receive_update(self, timeout: Optional[float] = None) -> Updates:
        """Wait for the next pushed frame and return it decrypted. [WS]"""
        self._require_user_session("receive_update")
        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("Receiving updates requires an authenticated session")
        await self._ensure_socket()
        if self._socket is None:
            raise TransportError("Socket transport is not available (enable_socket=False)")
        while True:
            frame = await self._socket.recv(timeout=timeout)
            if frame.get("type") == "messenger" and "data_enc" in frame:
                return self._decode_socket_frame(frame, auth)
            log.debug("Ignoring socket frame without updates: %s", list(frame))

    async def receive_socket_update(self, timeout: Optional[float] = None) -> Updates:
        """rubigram 0.1 name of :meth:`receive_update`."""
        return await self.receive_update(timeout=timeout)

    def _decode_socket_frame(self, frame: Dict[str, Any], auth: str) -> Updates:
        assert self._codec is not None
        try:
            decrypted = self._codec.decrypt_response({"data_enc": frame["data_enc"]}, auth)
        except Exception as exc:
            raise DecodeError(f"Failed to decrypt a socket frame: {exc}") from exc
        return Updates._parse(self, decrypted)

    # -- polling ----------------------------------------------------------------

    async def get_chats_updates(self, state: Optional[int] = None) -> ChatsUpdates:
        """``getChatsUpdates`` since ``state`` (defaults to the stored state); persists ``new_state``. [HTTP]"""
        if state is None:
            state = await self.storage.updates_state()
        if state is None:
            import time

            state = int(time.time())
        result = await self.invoke(GetChatsUpdates(state=state))
        if result.new_state is not None and not result.is_old_state:
            await self.storage.set_updates_state(result.new_state)
        return result

    async def get_messages_updates(self, object_guid: Any, state: Optional[int] = None) -> MessagesUpdates:
        """``getMessagesUpdates`` for one chat; the per-chat state is persisted. [HTTP]"""
        guid = self._resolve_object_guid(object_guid)
        if state is None:
            state = await self.storage.chat_state(guid)
        if state is None:
            import time

            state = int(time.time())
        result = await self.invoke(GetMessagesUpdates(object_guid=guid, state=state))
        if result.new_state is not None and not result.is_old_state:
            await self.storage.set_chat_state(guid, result.new_state)
        return result

    async def get_updates(self, *, timeout: Optional[float] = None, transport: str | Transport | None = None, **kwargs: Any) -> Any:
        """Fetch pending updates.

        - bots: ``getUpdates`` (Bot API long polling) → :class:`~rubigram.types.bot.BotUpdates`;
        - user sessions over ``Transport.HTTP`` (or ``transport="http"``): ``getChatsUpdates``;
        - user sessions over ``Transport.WS``: the next pushed frame (:class:`~rubigram.types.Updates`).
        [both]
        """
        if self.is_bot:
            return await self.get_bot_updates(**kwargs)
        mode = Transport.coerce(transport) if transport is not None else self.transport
        if mode.is_http:
            return await self.get_chats_updates(kwargs.get("state"))
        return await self.receive_update(timeout=timeout)

    # -- background listener -----------------------------------------------------

    async def _ensure_listener(self, *, force: bool = False) -> None:
        """Start the background update loop when handlers are registered (or ``force``).

        Without handlers nothing is polled, so :meth:`receive_update` /
        :meth:`get_updates` can be driven manually.
        """
        if self._listener_task is not None and not self._listener_task.done():
            return
        if not force and not self._dispatcher.has_handlers():
            return
        if self.is_bot:
            self._idle_event.clear()
            self._listener_task = asyncio.create_task(self._bot_polling_loop(), name="rubigram-bot-polling")
            return
        if not await self.storage.auth():
            return
        self._idle_event.clear()
        if self.transport.is_ws and self.enable_socket:
            self._listener_task = asyncio.create_task(self._socket_listener_loop(), name="rubigram-socket-listener")
        else:
            self._listener_task = asyncio.create_task(self._http_polling_loop(), name="rubigram-http-polling")

    async def _stop_listener(self) -> None:
        task = self._listener_task
        self._listener_task = None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task

    async def _socket_listener_loop(self) -> None:
        try:
            while self._is_connected:
                try:
                    updates = await self.receive_update()
                except asyncio.CancelledError:
                    raise
                except (TransportError, NetworkError, DecodeError) as exc:
                    log.warning("Update listener recovering from a socket error: %s", exc)
                    await asyncio.sleep(1)
                    continue
                try:
                    await self._dispatcher.dispatch_updates(updates)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception("Dispatching an update failed")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Update listener stopped because of an unexpected error")
        finally:
            self._idle_event.set()

    async def _http_polling_loop(self) -> None:
        """Approximate push delivery with ``getChatsUpdates``: new ``last_message`` entries become message events."""
        seen: Dict[str, str] = {}
        try:
            while self._is_connected:
                try:
                    result = await self.get_chats_updates()
                except asyncio.CancelledError:
                    raise
                except RubigramError as exc:
                    log.warning("Polling recovering from an error: %s", exc)
                    await asyncio.sleep(max(self.poll_interval, 1.0))
                    continue
                updates = Updates(client=self)
                for chat in result.chats:
                    message = chat.last_message
                    if message is None or not chat.object_guid or not message.message_id:
                        continue
                    if seen.get(chat.object_guid) == message.message_id:
                        continue
                    first_time = chat.object_guid not in seen
                    seen[chat.object_guid] = message.message_id
                    if first_time:
                        continue
                    message.object_guid = message.object_guid or chat.object_guid
                    updates.message_updates.append(
                        MessageUpdate(
                            client=self,
                            message_id=message.message_id,
                            action="New",
                            message=message,
                            object_guid=chat.object_guid,
                            type=chat.type,
                        )
                    )
                if not updates.is_empty:
                    with contextlib.suppress(Exception):
                        await self._dispatcher.dispatch_updates(updates)
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            raise
        finally:
            self._idle_event.set()

    async def _bot_polling_loop(self) -> None:
        try:
            while self._is_connected:
                try:
                    updates = await self.get_bot_updates()
                except asyncio.CancelledError:
                    raise
                except RubigramError as exc:
                    log.warning("Bot polling recovering from an error: %s", exc)
                    await asyncio.sleep(max(self.poll_interval, 1.0))
                    continue
                for update in updates.updates:
                    with contextlib.suppress(Exception):
                        await self._dispatcher.dispatch_bot_update(update)
                if not updates.updates:
                    await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            raise
        finally:
            self._idle_event.set()

    async def idle(self) -> None:
        """Keep receiving updates until :meth:`stop` is called or the loop is cancelled. [both]"""
        await self._ensure_listener(force=True)
        self._idle_event.clear()
        await self._idle_event.wait()

    async def start_polling(self, *, limit: int = 100, idle_sleep: Optional[float] = None) -> None:
        """rubigram 0.1 bot API: start the background polling loop."""
        if idle_sleep is not None:
            self.poll_interval = idle_sleep
        self._bot_poll_limit = limit
        await self._ensure_listener(force=True)

    async def stop_polling(self) -> None:
        """Stop the background update loop started by :meth:`start_polling` or :meth:`idle`. [both]"""
        await self._stop_listener()

    async def dispatch_update(self, update: Any) -> None:
        """Feed an update object (``Updates``, bot ``Update`` or ``InlineMessage``) to the handlers."""
        from rubigram.types.bot import InlineMessage, Update

        if isinstance(update, Updates):
            await self._dispatcher.dispatch_updates(update)
        elif isinstance(update, Update):
            await self._dispatcher.dispatch_bot_update(update)
        elif isinstance(update, InlineMessage):
            await self._dispatcher.dispatch_inline_message(update)
        else:
            await self._dispatcher.dispatch("raw", update)


__all__ = ["UpdatesMixin"]
