"""The interface every method mixin can rely on.

:class:`BaseClient` declares the attributes :class:`~rubigram.Client` sets in
its constructor and the handful of methods mixins call on each other, so each
mixin type-checks on its own.  The concrete implementations live in the
mixins (they precede this class in the MRO); the stubs here are never reached
at runtime.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence, TypeVar, Union

from rubigram.network import Transport
from rubigram.peer import Peer
from rubigram.utils import new_rnd

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.crypto import Codec
    from rubigram.handlers import Dispatcher
    from rubigram.network import (
        BotTransport,
        DcDiscovery,
        DcRepository,
        DownloadTransport,
        HttpTransport,
        JsonTransport,
        RetryPolicy,
        SocketTransport,
        UploadTransport,
    )
    from rubigram.raw.base import RawMethod
    from rubigram.storage import Storage
    from rubigram.types import Authorization, Empty, UploadDescriptor
    from rubigram.types.bot import BotUpdates
    from rubigram.types.bot import Chat as BotChat
    from rubigram.types.bot import SentMessage as BotSentMessage

ResultT = TypeVar("ResultT")
PeerLike = Any
CodeCallback = Callable[..., Union[str, Awaitable[str]]]


class RubigramMisuse(TypeError):
    """Raised when a mixin stub is reached, which means the mixin was used outside ``Client``."""


def _stub(name: str) -> Any:
    raise RubigramMisuse(f"{name} is only available on rubigram.Client")


class BaseClient:
    """Attributes and cross-mixin hooks shared by all method mixins."""

    # -- class constants (overridable) -----------------------------------------
    APP_NAME: str
    APP_VERSION: str
    PLATFORM: str
    PWA_PLATFORM: str
    PACKAGE: str
    LANG_CODE: str
    SYSTEM_VERSION: str
    DEVICE_MODEL: str
    REGISTER_DEVICE_APP_VERSION_PREFIX: str
    REGISTER_DEVICE_TOKEN_TYPE: str
    SOCKET_HANDSHAKE_API_VERSION: str
    SOCKET_HEARTBEAT_INTERVAL: float

    # -- constructor state -------------------------------------------------------
    name: str
    workdir: Path
    session_string: Optional[str]
    token: Optional[str]
    in_memory: bool
    pem_private_key: Optional[str]
    timeout: float
    proxy: Optional[str]
    user_agent: str
    app_version: str
    lang_code: str
    system_version: str
    device_model: str
    device_hash: Optional[str]
    phone_number: Optional[str]
    phone_code: Optional[str]
    first_name: Optional[str]
    last_name: str
    code_callback: Optional[CodeCallback]
    interactive: bool
    socket_urls: List[str]
    enable_socket: bool
    enable_register_device: bool
    retry_policy: RetryPolicy
    poll_interval: float
    socket_heartbeat_interval: float
    device_info: Dict[str, str]
    session_invalid: bool
    storage: Storage
    dc: DcRepository

    _transport_mode: Transport
    _discovery: Optional[DcDiscovery]
    _http: Optional[HttpTransport]
    _bot_dc_http: Optional[HttpTransport]
    _service: Optional[JsonTransport]
    _socket: Optional[SocketTransport]
    _upload: Optional[UploadTransport]
    _download: Optional[DownloadTransport]
    _bot: Optional[BotTransport]
    _codec: Optional[Codec]
    _dispatcher: Dispatcher
    _is_connected: bool
    _listener_task: Optional[asyncio.Task[None]]
    _idle_event: asyncio.Event
    _bot_last_offset_id: Optional[str]
    _bot_poll_limit: Optional[int]
    _cached_user_guid: Optional[str]
    _register_lock: asyncio.Lock

    # -- trivial properties ---------------------------------------------------------

    @property
    def is_bot(self) -> bool:
        """``True`` for ``Client(token=...)`` sessions."""
        return bool(self.token)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def transport(self) -> Transport:
        """Update delivery mode (``Transport.WS`` or ``Transport.HTTP``)."""
        return self._transport_mode

    @property
    def dispatcher(self) -> Dispatcher:
        return self._dispatcher

    @property
    def client_info(self) -> Dict[str, str]:
        """The ``client`` block of encrypted RPCs."""
        return dict(self.device_info)

    @property
    def service_client_info(self) -> Dict[str, str]:
        """The ``client`` block of service calls (platform ``PWA``)."""
        return {
            "app_name": self.device_info.get("app_name", self.APP_NAME),
            "app_version": self.device_info.get("app_version", self.app_version),
            "platform": self.PWA_PLATFORM,
            "package": self.device_info.get("package", self.PACKAGE),
        }

    # -- shared helpers -----------------------------------------------------------------

    @staticmethod
    def _new_rnd() -> str:
        return new_rnd()

    @staticmethod
    def _resolve_peer(peer: PeerLike) -> Peer:
        return Peer.from_value(peer)

    @staticmethod
    def _resolve_object_guid(object_guid: PeerLike = None, *, peer: PeerLike = None) -> str:
        candidate = peer if peer is not None else object_guid
        if candidate is None:
            raise ValueError("Either object_guid or peer must be provided")
        return Peer.from_value(candidate).object_guid

    @staticmethod
    def _resolve_user_guid(user_guid: PeerLike) -> str:
        resolved = Peer.from_value(user_guid).user_guid
        if not resolved:
            raise ValueError("user_guid could not be resolved from peer")
        return resolved

    @classmethod
    def _resolve_guids(cls, values: Optional[Iterable[PeerLike]]) -> List[str]:
        return [cls._resolve_object_guid(value) for value in (values or ())]

    @staticmethod
    def _plain_list(values: Optional[Sequence[Any]]) -> List[str]:
        return [str(getattr(item, "value", item)) for item in (values or ())]

    def _require_user_session(self, what: str = "This method") -> None:
        from rubigram.errors import RubigramError

        if self.is_bot:
            raise RubigramError(f"{what} is only available on a phone-number (user) session")

    def _require_bot(self, what: str = "This method") -> BotTransport:
        from rubigram.errors import RubigramError

        if not self.is_bot or self._bot is None:
            raise RubigramError(f"{what} is only available on a bot-token session")
        return self._bot

    # -- hooks implemented by other mixins (stubs) ----------------------------------------

    async def invoke(self, method: RawMethod[ResultT], *, timeout: Optional[float] = None, retries: Optional[int] = None) -> ResultT:
        return _stub("invoke")

    async def _call_rpc(
        self, method: RawMethod[Any], *, timeout: Optional[float], retries: Optional[int], allow_register_retry: bool
    ) -> Any:
        return _stub("_call_rpc")

    async def _finalize_login(self, encrypted_auth: str, data: Dict[str, Any]) -> None:
        _stub("_finalize_login")

    async def login(
        self,
        phone_number: Optional[str] = None,
        *,
        code: Optional[str] = None,
        code_callback: Optional[CodeCallback] = None,
        password: Optional[str] = None,
        max_attempts: int = 3,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Authorization:
        return _stub("login")

    async def register_device(self, force: bool = False) -> Empty:
        return _stub("register_device")

    async def _ensure_registered_device(self, force: bool = False) -> None:
        _stub("_ensure_registered_device")

    async def _ensure_login_key_pair(self) -> None:
        _stub("_ensure_login_key_pair")

    async def _ensure_socket(self, force_reconnect: bool = False) -> None:
        _stub("_ensure_socket")

    async def _ensure_listener(self, *, force: bool = False) -> None:
        _stub("_ensure_listener")

    async def _stop_listener(self) -> None:
        _stub("_stop_listener")

    async def _ensure_base_info(self, force: bool = False) -> Optional[Dict[str, str]]:
        return _stub("_ensure_base_info")

    async def idle(self) -> None:
        _stub("idle")

    async def send_message(self, object_guid: Any = None, text: Optional[str] = None, rnd: Optional[str] = None, **kwargs: Any) -> Any:
        return _stub("send_message")

    async def edit_message(self, object_guid: Any = None, message_id: Any = "", text: str = "", **kwargs: Any) -> Any:
        return _stub("edit_message")

    async def request_send_file(
        self, file_name: Optional[str] = None, size: Optional[int] = None, mime: Optional[str] = None, *, type: Any = None
    ) -> Any:
        return _stub("request_send_file")

    async def upload_file(self, path: Union[str, Path, None] = None, **kwargs: Any) -> Any:
        return _stub("upload_file")

    async def upload_bot_file(self, upload_url: str, path: Union[str, Path]) -> str:
        return _stub("upload_bot_file")

    async def download_bot_file(
        self, file: Any, path: Union[str, Path, None] = None, *, in_memory: bool = False, file_name: Optional[str] = None
    ) -> Union[bytes, Path]:
        return _stub("download_bot_file")

    async def send_file(self, chat_id: Any, file_id: str, **kwargs: Any) -> BotSentMessage:
        return _stub("send_file")

    async def get_bot_updates(self, offset_id: Optional[str] = None, limit: Optional[int] = None) -> BotUpdates:
        return _stub("get_bot_updates")

    async def _bot_get_me(self) -> Any:
        return _stub("_bot_get_me")

    async def _bot_get_chat(self, chat_id: str) -> BotChat:
        return _stub("_bot_get_chat")

    async def _bot_send_message(
        self,
        *,
        chat_id: str,
        text: str,
        chat_keypad: Any = None,
        inline_keypad: Any = None,
        chat_keypad_type: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: Optional[str] = None,
    ) -> BotSentMessage:
        return _stub("_bot_send_message")

    async def _bot_send_location(
        self, chat_id: str, latitude: str, longitude: str, *, reply_to_message_id: Optional[str] = None, **kwargs: Any
    ) -> BotSentMessage:
        return _stub("_bot_send_location")

    async def _bot_send_poll(self, chat_id: str, question: str, options: List[str]) -> BotSentMessage:
        return _stub("_bot_send_poll")

    async def _bot_forward_message(
        self, from_chat_id: str, message_id: str, to_chat_id: str, *, disable_notification: bool = False
    ) -> BotSentMessage:
        return _stub("_bot_forward_message")

    async def _bot_edit_message_text(self, chat_id: str, message_id: str, text: str) -> BotSentMessage:
        return _stub("_bot_edit_message_text")

    async def _bot_delete_message(self, chat_id: str, message_id: str) -> bool:
        return _stub("_bot_delete_message")

    async def _bot_request_send_file(self, file_type: str) -> Dict[str, Any]:
        return _stub("_bot_request_send_file")

    async def _bot_send_media(
        self,
        chat_id: str,
        path: Union[str, Path],
        *,
        file_type: str,
        text: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        **kwargs: Any,
    ) -> BotSentMessage:
        return _stub("_bot_send_media")

    def _resolve_download_destination(self, path: Union[str, Path, None], file_name: str) -> Path:
        return _stub("_resolve_download_destination")

    def _default_file_name_from_url(self, url: str) -> str:
        return _stub("_default_file_name_from_url")

    async def _upload_file(
        self, *, path: Union[str, Path], descriptor: UploadDescriptor, progress: Any = None, progress_args: tuple[Any, ...] = ()
    ) -> UploadDescriptor:
        return _stub("_upload_file")


__all__ = ["BaseClient", "CodeCallback", "PeerLike", "RubigramMisuse"]
