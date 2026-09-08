"""The thin client: construction, lifecycle, transports, handler registration."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Sequence, Union

from rubigram.client.base import CodeCallback
from rubigram.client.methods import Methods
from rubigram.crypto import AuthSigner, AuthUnwrapper, Codec
from rubigram.enums import DcType
from rubigram.errors import AuthError, RubigramError, is_ok, map_rpc_error
from rubigram.handlers import (
    ActivityHandler,
    CallbackQueryHandler,
    ChatUpdateHandler,
    DeletedMessageHandler,
    Dispatcher,
    DraftUpdateHandler,
    EditedMessageHandler,
    Handler,
    InlineMessageHandler,
    MessageHandler,
    NotificationHandler,
    RawUpdateHandler,
)
from rubigram.network import (
    DEFAULT_RETRY_POLICY,
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
)
from rubigram.network.headers import CHROME_USER_AGENT
from rubigram.raw.functions.envelope import APP_NAME, APP_VERSION, LANG_CODE, PACKAGE, PLATFORM_PWA, PLATFORM_WEB, VERSION_PREFIX
from rubigram.storage import MemoryStorage, SqliteStorage, Storage
from rubigram.version import __version__

log = logging.getLogger(__name__)


class Client(Methods):
    """Rubika client for phone-number sessions and bot tokens.

    Example::

        app = Client("my_account")            # session stored in ./my_account.session
        bot = Client("my_bot", token="…")     # Bot API mode

        @app.on_message(filters.text & filters.private)
        async def echo(client, message):
            await message.reply(message.text)

        app.run()
    """

    APP_NAME = APP_NAME
    APP_VERSION = APP_VERSION
    PLATFORM = PLATFORM_WEB
    PWA_PLATFORM = PLATFORM_PWA
    PACKAGE = PACKAGE
    LANG_CODE = LANG_CODE
    SYSTEM_VERSION = "Windows 10"
    DEVICE_MODEL = "Chrome 145"
    REGISTER_DEVICE_APP_VERSION_PREFIX = VERSION_PREFIX
    REGISTER_DEVICE_TOKEN_TYPE = "Web"
    SOCKET_HANDSHAKE_API_VERSION = "5"
    SOCKET_HEARTBEAT_INTERVAL = 30.0
    DEFAULT_SOCKET_URLS: tuple[str, ...] = ()

    def __init__(
        self,
        name: str,
        workdir: Union[str, Path] = Path("."),
        *,
        session_string: Optional[str] = None,
        token: Optional[str] = None,
        in_memory: bool = False,
        storage: Optional[Storage] = None,
        pem_private_key: Optional[str] = None,
        timeout: float = 20.0,
        proxy: Optional[str] = None,
        transport: str | Transport = Transport.WS,
        user_agent: Optional[str] = None,
        app_version: Optional[str] = None,
        lang_code: Optional[str] = None,
        device_info: Optional[Dict[str, str]] = None,
        system_version: str = SYSTEM_VERSION,
        device_model: str = DEVICE_MODEL,
        device_hash: Optional[str] = None,
        phone_number: Optional[str] = None,
        phone_code: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: str = "",
        code_callback: Optional[CodeCallback] = None,
        interactive: Optional[bool] = None,
        socket_urls: Optional[Sequence[str]] = None,
        enable_socket: Optional[bool] = None,
        enable_register_device: bool = True,
        retry_policy: Optional[RetryPolicy] = None,
        poll_interval: float = 5.0,
        discover_dcs: bool = True,
        refresh_base_info: bool = True,
        # rubigram 0.1 keyword names
        interactive_auth: Optional[bool] = None,
        enable_socket_handshake: Optional[bool] = None,
        socket_heartbeat_interval: Optional[float] = None,
    ):
        self.name = name
        self.workdir = Path(workdir) if workdir else Path(".")
        self.session_string = session_string
        self.token = token
        self.in_memory = in_memory
        self.pem_private_key = pem_private_key
        self.timeout = timeout
        self.proxy = proxy
        self.user_agent = user_agent or CHROME_USER_AGENT
        self.app_version = app_version or self.APP_VERSION
        self.lang_code = lang_code or self.LANG_CODE
        self.system_version = system_version
        self.device_model = device_model
        self.device_hash = device_hash
        self.phone_number = phone_number
        self.phone_code = phone_code
        self.first_name = first_name
        self.last_name = last_name
        self.code_callback = code_callback
        self.interactive = interactive if interactive is not None else (interactive_auth if interactive_auth is not None else True)
        self.socket_urls = list(socket_urls or self.DEFAULT_SOCKET_URLS)
        self.enable_socket = (
            enable_socket if enable_socket is not None else (enable_socket_handshake if enable_socket_handshake is not None else True)
        )
        self.enable_register_device = enable_register_device
        self.retry_policy = retry_policy or DEFAULT_RETRY_POLICY
        self.poll_interval = poll_interval
        self.discover_dcs = discover_dcs
        self.refresh_base_info = refresh_base_info
        self.socket_heartbeat_interval = socket_heartbeat_interval or self.SOCKET_HEARTBEAT_INTERVAL
        self.device_info: Dict[str, str] = (
            dict(device_info)
            if device_info
            else {
                "app_name": self.APP_NAME,
                "app_version": self.app_version,
                "platform": self.PLATFORM,
                "package": self.PACKAGE,
                "lang_code": self.lang_code,
            }
        )
        self._transport_mode = Transport.coerce(transport)

        if storage is not None:
            self.storage: Storage = storage
        elif session_string:
            self.storage = MemoryStorage(name, session_string)
        elif in_memory:
            self.storage = MemoryStorage(name)
        else:
            self.storage = SqliteStorage(name, self.workdir)

        self.dc = DcRepository()
        self._discovery: Optional[DcDiscovery] = None
        self._http: Optional[HttpTransport] = None
        self._bot_dc_http: Optional[HttpTransport] = None
        self._service: Optional[JsonTransport] = None
        self._socket: Optional[SocketTransport] = None
        self._upload: Optional[UploadTransport] = None
        self._download: Optional[DownloadTransport] = None
        self._bot: Optional[BotTransport] = None
        self._codec: Optional[Codec] = None
        self._dispatcher = Dispatcher(self)
        self._is_connected = False
        self._listener_task: Optional[asyncio.Task[None]] = None
        self._idle_event = asyncio.Event()
        self._bot_last_offset_id: Optional[str] = None
        self._bot_poll_limit: Optional[int] = None
        self._cached_user_guid: Optional[str] = None
        self._register_lock = asyncio.Lock()
        self.session_invalid = False

    # -- factories ------------------------------------------------------------

    @classmethod
    def from_session_string(cls, name: str, session_string: str, **kwargs: Any) -> Client:
        """Create an in-memory client from a portable session string."""
        return cls(name, session_string=session_string, **kwargs)

    # -- properties -----------------------------------------------------------

    def set_transport(self, mode: str | Transport) -> None:
        """Switch the update delivery mode; the socket is opened or closed lazily."""
        self._transport_mode = Transport.coerce(mode)

    @contextlib.asynccontextmanager
    async def use_transport(self, mode: str | Transport):
        """Temporarily switch the transport mode for the duration of the block."""
        previous = self._transport_mode
        self._transport_mode = Transport.coerce(mode)
        try:
            yield self
        finally:
            self._transport_mode = previous

    @property
    def socket(self) -> Optional[SocketTransport]:
        return self._socket

    # -- lifecycle ------------------------------------------------------------

    async def __aenter__(self) -> Client:
        return await self.start()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> Client:
        """Open the session, discover DCs, log in if needed and connect."""
        if self._is_connected:
            return self
        await self.storage.open()
        try:
            if self.token is not None:
                await self.storage.set_bot_token(self.token)
            self.token = self.token or await self.storage.bot_token()
            self._bot_last_offset_id = await self.storage.bot_offset_id()
            if self.is_bot:
                self._bot = BotTransport(str(self.token), timeout=self.timeout, proxy=self.proxy, retry_policy=self.retry_policy)
                self._is_connected = True
                await self._ensure_listener()
                return self
            await self._start_user_session()
        except Exception:
            await self._safe_close()
            raise
        return self

    async def _start_user_session(self) -> None:
        self._discovery = DcDiscovery(timeout=self.timeout, proxy=self.proxy, client_info=self.client_info, user_agent=self.user_agent)
        self.dc = DcRepository.from_dict(await self.storage.dc_repository())
        if self.discover_dcs or not self.dc.storages:
            await self._refresh_dcs(required=not self.dc.storages)
        self.dc.merge_urls(DcType.SOCKET, self.socket_urls)
        self._http = HttpTransport(
            self.dc.pool(DcType.API),
            timeout=self.timeout,
            proxy=self.proxy,
            retry_policy=self.retry_policy,
            refresh_urls=self._refresh_api_urls,
            user_agent=self.user_agent,
        )
        self._bot_dc_http = HttpTransport(
            self.dc.pool(DcType.BOT), timeout=self.timeout, proxy=self.proxy, retry_policy=self.retry_policy, user_agent=self.user_agent
        )
        self._service = JsonTransport(
            self.dc.pool(DcType.API), timeout=self.timeout, proxy=self.proxy, retry_policy=self.retry_policy, user_agent=self.user_agent
        )
        self._upload = UploadTransport(
            timeout=max(self.timeout, 30.0), proxy=self.proxy, retry_policy=self.retry_policy, user_agent=self.user_agent
        )
        self._download = DownloadTransport(
            timeout=max(self.timeout, 30.0), proxy=self.proxy, retry_policy=self.retry_policy, user_agent=self.user_agent
        )
        current_url = await self.storage.api_url()
        if current_url:
            self.dc.pool(DcType.API).set_current(current_url)
        self._cached_user_guid = await self.storage.user_guid()
        await self._ensure_login_key_pair()
        private_key_pem = await self.storage.private_key_pem()
        if not private_key_pem:
            raise AuthError("Missing private key for the login flow")
        self._codec = Codec(AuthSigner(private_key_pem), AuthUnwrapper(private_key_pem))
        self._is_connected = True

        if not await self.storage.auth() and self._should_login_on_start():
            await self.login()
        if await self.storage.auth():
            await self._after_login()

    async def _after_login(self) -> None:
        if self.refresh_base_info:
            try:
                await self._ensure_base_info(force=True)
            except RubigramError as exc:
                log.warning("Base info refresh failed during startup: %s", exc)
        await self._ensure_registered_device()
        if self._transport_mode.is_ws and self.enable_socket:
            try:
                await self._ensure_socket()
            except RubigramError as exc:
                log.warning("Socket connection failed during startup: %s", exc)
        await self._ensure_listener()

    def _should_login_on_start(self) -> bool:
        if self.is_bot:
            return False
        if self.phone_number or self.code_callback:
            return True
        if not self.interactive:
            return False
        return bool(getattr(sys.stdin, "isatty", lambda: False)() and getattr(sys.stdout, "isatty", lambda: False)())

    async def _refresh_dcs(self, *, required: bool) -> None:
        assert self._discovery is not None
        try:
            payload = await self._discovery.fetch_dcs()
        except RubigramError as exc:
            if required:
                raise
            log.warning("DC discovery failed, using the cached configuration: %s", exc)
            return
        if not is_ok(payload):
            raise map_rpc_error(str(payload.get("status")), payload.get("status_det"), payload, method="getDCs")
        self.dc.update_from_dcs(payload)
        await self.storage.set_dc_repository(self.dc.to_dict())
        await self.storage.set_api_urls(self.dc.api_urls)
        await self.storage.set_sockets(self.dc.socket_urls)
        await self.storage.set_storages(self.dc.storages)
        await self.storage.set_cdn_urls(self.dc.cdn_urls)

    async def _refresh_api_urls(self) -> Optional[list[str]]:
        try:
            await self._refresh_dcs(required=True)
        except RubigramError:
            return None
        return self.dc.api_urls

    async def stop(self) -> None:
        """Close every transport and the storage."""
        await self._safe_close()

    def run(self, coroutine: Optional[Awaitable[Any]] = None) -> None:
        """Start the client, run ``coroutine`` (or idle until Ctrl-C), then stop."""

        async def main() -> None:
            await self.start()
            try:
                if coroutine is not None:
                    await coroutine
                else:
                    await self.idle()
            finally:
                await self.stop()

        with contextlib.suppress(KeyboardInterrupt):  # pragma: no cover - interactive
            asyncio.run(main())

    # -- handler registration -------------------------------------------------

    def add_handler(self, handler: Handler, group: int = 0) -> Handler:
        """Register a :class:`~rubigram.handlers.Handler` instance in ``group``."""
        return self._dispatcher.add_handler(handler, group)

    def remove_handler(self, handler: Handler, group: Optional[int] = None) -> bool:
        """Unregister a handler; returns whether it was found."""
        return self._dispatcher.remove_handler(handler, group)

    def _decorator(self, handler_cls: type[Handler], filters: Any, group: int):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_handler(handler_cls(func, filters), group)
            return func

        return decorator

    def on_message(self, filters: Any = None, group: int = 0):
        """Register a handler for new messages (user sessions and bots)."""
        return self._decorator(MessageHandler, filters, group)

    def on_edited_message(self, filters: Any = None, group: int = 0):
        """Register a handler for edited messages (``action == "Edit"``; bot ``UpdatedMessage``). [both]"""
        return self._decorator(EditedMessageHandler, filters, group)

    def on_deleted_message(self, filters: Any = None, group: int = 0):
        """Register a handler for deleted messages (``action == "Delete"``; bot ``RemovedMessage``). [both]"""
        return self._decorator(DeletedMessageHandler, filters, group)

    def on_chat_update(self, filters: Any = None, group: int = 0):
        """Register a handler for chat list changes (``chat_updates``: unread counts, pins, new chats). [WS]"""
        return self._decorator(ChatUpdateHandler, filters, group)

    def on_activity(self, filters: Any = None, group: int = 0):
        """Register a handler for typing/recording/uploading activities (``show_activities``). [WS]"""
        return self._decorator(ActivityHandler, filters, group)

    def on_notification(self, filters: Any = None, group: int = 0):
        """Register a handler for ``show_notifications`` entries. [WS]"""
        return self._decorator(NotificationHandler, filters, group)

    def on_draft_update(self, filters: Any = None, group: int = 0):
        """Register a handler for draft changes (``draft_message_updates``). [WS]"""
        return self._decorator(DraftUpdateHandler, filters, group)

    def on_inline_message(self, filters: Any = None, group: int = 0):
        """Register a handler for bot inline messages delivered by webhooks. [bot]"""
        return self._decorator(InlineMessageHandler, filters, group)

    def on_callback_query(self, filters: Any = None, group: int = 0):
        """Register a handler for bot button presses (messages carrying ``aux_data.button_id``). [bot]"""
        return self._decorator(CallbackQueryHandler, filters, group)

    def on_raw_update(self, filters: Any = None, group: int = 0):
        """Register a handler that receives every decrypted frame (:class:`~rubigram.types.Updates`) or bot update. [both]"""
        return self._decorator(RawUpdateHandler, filters, group)

    # -- internals --------------------------------------------------------------

    async def _safe_close(self) -> None:
        await self._stop_listener()
        self._idle_event.set()
        for attr in ("_socket", "_http", "_bot_dc_http", "_service", "_upload", "_download", "_bot", "_discovery"):
            transport = getattr(self, attr)
            setattr(self, attr, None)
            if transport is not None:
                with contextlib.suppress(Exception):
                    await transport.close()
        with contextlib.suppress(Exception):
            await self.storage.close()
        self._codec = None
        self._is_connected = False
        self._cached_user_guid = None

    def __repr__(self) -> str:
        mode = "bot" if self.is_bot else "user"
        return f"rubigram.Client(name={self.name!r}, mode={mode}, transport={self._transport_mode.value}, version={__version__})"


__all__ = ["Client", "CodeCallback"]
