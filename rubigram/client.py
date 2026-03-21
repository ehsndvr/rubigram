from __future__ import annotations

import asyncio
import inspect
import logging
import mimetypes
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, TypeVar, Union

from . import crypto, raw
from . import filters as rubigram_filters
from .enums import ParseMode
from rubigram.crypto import (
    AuthSigner,
    AuthUnwrapper,
    Codec,
    export_public_key_for_login,
    generate_rsa_key_pair,
)
from rubigram.exceptions import (
    AuthError,
    CodeIsInvalid,
    DecodeError,
    InvalidInput,
    LoginRequired,
    NetworkError,
    PhoneCodeInvalid,
    PhoneHashInvalid,
    RegisterDeviceRequired,
    RubikaError,
    TransportError,
    map_rpc_error,
)
from rubigram.network.discovery import DcDiscovery
from rubigram.network.socket import SocketTransport
from rubigram.network.transport import ApiUrlPool, RpcTransport
from rubigram.network.upload import UploadTransport
from rubigram.network.download import DownloadTransport
from rubigram.methods import Methods
from rubigram.raw.base import RawMethod
from rubigram.raw.methods import (
    BlockUser,
    DeleteMessage,
    EditMessage,
    GetAvatars,
    GetChat,
    GetChatsUpdates,
    GetContacts,
    GetHistory,
    GetMessages,
    GetObjectByUsername,
    GetUserInfo,
    RequestSendFile,
    RegisterDevice,
    SendCode,
    SendMessage,
    SignIn,
    SignUp,
    UnblockUser,
)
from rubigram.storage.file_storage import FileStorage
from rubigram.storage.memory_storage import MemoryStorage
from rubigram.storage.sqlite_storage import SQLiteStorage
from rubigram.types import (
    Authorization,
    ChatAvatars,
    ChatsUpdates,
    Empty,
    MessageEntity,
    ObjectByUsername,
    RawObject,
    SentCode,
    SentMessage,
    SocketUpdates,
    UploadDescriptor,
    UserInfo,
)
from rubigram.utils import generate_device_hash, generate_tmp_session
from rubigram.version import __version__

log = logging.getLogger(__name__)
ResultT = TypeVar("ResultT")


class MessageHandler:
    def __init__(self, callback: Any, flt: Any):
        self.callback = callback
        self.filter = flt


class Client(Methods):
    """Raw-first Rubika HTTP client."""

    raw = raw
    crypto = crypto
    filters = rubigram_filters

    APP_NAME = "Main"
    APP_VERSION = "4.4.27"
    PLATFORM = "Web"
    PACKAGE = "web.rubika.ir"
    LANG_CODE = "fa"
    SYSTEM_VERSION = "Windows 10"
    DEVICE_MODEL = "Chrome 145"
    REGISTER_DEVICE_APP_VERSION_PREFIX = "WB_"
    REGISTER_DEVICE_TOKEN_TYPE = "Web"
    SOCKET_HANDSHAKE_API_VERSION = "5"
    SOCKET_HEARTBEAT_INTERVAL = 30.0
    DEFAULT_SOCKET_URLS: tuple[str, ...] = ()

    def __init__(
        self,
        name: str,
        workdir: Union[str, Path] = Path("."),
        session_string: Optional[str] = None,
        in_memory: bool = False,
        pem_private_key: Optional[str] = None,
        timeout: float = 20.0,
        device_info: Optional[Dict[str, str]] = None,
        system_version: str = SYSTEM_VERSION,
        device_model: str = DEVICE_MODEL,
        device_hash: Optional[str] = None,
        phone_number: Optional[str] = None,
        phone_code: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: str = "",
        interactive_auth: bool = True,
        socket_urls: Optional[list[str]] = None,
        enable_socket_handshake: bool = True,
        enable_register_device: bool = True,
        socket_heartbeat_interval: float = SOCKET_HEARTBEAT_INTERVAL,
    ):
        self.name = name
        self.workdir = Path(workdir) if workdir else Path(".")
        self.session_string = session_string
        self.in_memory = in_memory
        self.timeout = timeout
        self.pem_private_key = pem_private_key
        self.system_version = system_version
        self.device_model = device_model
        self.device_hash = device_hash
        self.phone_number = phone_number
        self.phone_code = phone_code
        self.first_name = first_name
        self.last_name = last_name
        self.interactive_auth = interactive_auth
        self.socket_urls = socket_urls or list(self.DEFAULT_SOCKET_URLS)
        self.enable_socket_handshake = enable_socket_handshake
        self.enable_register_device = enable_register_device
        self.socket_heartbeat_interval = socket_heartbeat_interval
        self.device_info = device_info or {
            "app_name": self.APP_NAME,
            "app_version": self.APP_VERSION,
            "platform": self.PLATFORM,
            "package": self.PACKAGE,
            "lang_code": self.LANG_CODE,
        }

        if session_string:
            self.storage: SQLiteStorage = MemoryStorage(name, session_string)
        elif in_memory:
            self.storage = MemoryStorage(name)
        else:
            self.storage = FileStorage(name, self.workdir)

        self._dc_discovery: Optional[DcDiscovery] = None
        self._pool: Optional[ApiUrlPool] = None
        self._transport: Optional[RpcTransport] = None
        self._upload_transport: Optional[UploadTransport] = None
        self._download_transport: Optional[DownloadTransport] = None
        self._socket_transport: Optional[SocketTransport] = None
        self._codec: Optional[Codec] = None
        self._is_connected = False
        self._message_handlers: list[MessageHandler] = []
        self._update_listener_task: Optional[asyncio.Task[None]] = None
        self._idle_event = asyncio.Event()

    def __enter__(self) -> Client:
        asyncio.run(self.start())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        asyncio.run(self.stop())

    async def __aenter__(self) -> Client:
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def start(self) -> Client:
        """Open storage, refresh DC configuration, and initialize transport."""
        if self._is_connected:
            return self

        await self.storage.open()
        self._dc_discovery = DcDiscovery(timeout=self.timeout)

        try:
            dc_response = await self._dc_discovery.fetch_dcs()
            self._raise_if_not_ok(dc_response)

            dc_data = dc_response.get("data", {})
            api_urls = dc_data.get("default_api_urls", [])
            if not api_urls:
                raise NetworkError("DC discovery returned no API URLs")

            await self.storage.set_api_urls(api_urls)
            await self.storage.set_storages(dc_data.get("storages", {}))
            await self.storage.set_cdn_urls(dc_data.get("default_cdn_urls", {}))
            await self.storage.set_sockets(dc_data.get("default_sockets", []))

            self._pool = ApiUrlPool(api_urls)

            current_url = await self.storage.api_url()
            if current_url and current_url in api_urls:
                self._pool._current_index = api_urls.index(current_url)
            else:
                await self.storage.set_api_url(self._pool.get_current())

            await self._ensure_login_key_pair()
            private_key_pem = await self.storage.private_key_pem()
            if not private_key_pem:
                raise AuthError("Missing private key for login/auth flow")

            self._codec = Codec(
                AuthSigner(private_key_pem),
                AuthUnwrapper(private_key_pem),
            )
            self._transport = RpcTransport(
                self._dc_discovery,
                self._pool,
                timeout=self.timeout,
            )
            self._upload_transport = UploadTransport(timeout=max(self.timeout, 60.0))
            self._download_transport = DownloadTransport(timeout=max(self.timeout, 60.0))
            self._is_connected = True
            if not await self.storage.auth() and self._should_interactive_authorize():
                await self.authorize()
            if await self.storage.auth():
                await self._ensure_socket_handshake()
                await self._ensure_registered_device()
                await self._ensure_update_listener()
        except Exception as e:
            print(f"Failed to start client: {e}")
            await self._safe_close()
            raise
        return self

    async def stop(self) -> None:
        await self._safe_close()
        self._is_connected = False

    async def export_session_string(self) -> str:
        return await self.storage.export_session_string()

    def on_message(self, flt: Any = None):
        flt = flt or rubigram_filters.all

        def decorator(func):
            self._message_handlers.append(MessageHandler(func, flt))
            return func

        return decorator

    async def idle(self) -> None:
        await self._ensure_update_listener()
        await self._idle_event.wait()

    async def send_code(self, phone_number: str) -> SentCode:
        return await self.invoke(SendCode(phone_number=self._normalize_phone_number(phone_number)))

    async def sign_in(
        self,
        phone_number: str,
        phone_code_hash: str,
        phone_code: str,
    ) -> Authorization:
        return await self.invoke(
            SignIn(
                phone_number=self._normalize_phone_number(phone_number),
                phone_code_hash=phone_code_hash,
                phone_code=phone_code,
            )
        )

    async def sign_up(
        self,
        first_name: str,
        last_name: str = "",
    ) -> Authorization:
        return await self.invoke(SignUp(first_name=first_name, last_name=last_name))

    async def register_device(self, force: bool = False) -> Empty:
        if not self.enable_register_device:
            return Empty()

        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("registerDevice requires an authenticated session")

        if not force:
            if await self.storage.registered_device() and await self.storage.registered_device_version() == self.APP_VERSION:
                return Empty()

        await self.storage.set_registered_device(False)
        await self.storage.set_registered_device_version(None)
        device_hash = await self._ensure_device_hash()
        result = await self._invoke_once(
            RegisterDevice(
                token_type=self.REGISTER_DEVICE_TOKEN_TYPE,
                token="",
                app_version=self._register_device_app_version(),
                lang_code=self.device_info["lang_code"],
                system_version=self.system_version,
                device_model=self.device_model,
                device_hash=device_hash,
            ),
            allow_register_retry=False,
        )
        await self.storage.set_registered_device(True)
        await self.storage.set_registered_device_version(self.APP_VERSION)
        return result

    async def request_send_file(self, file_name: str, size: int, mime: str) -> UploadDescriptor:
        return await self.invoke(RequestSendFile(file_name=file_name, size=size, mime=mime))

    async def get_user_info(self, user_guid: str) -> UserInfo:
        return await self.invoke(GetUserInfo(user_guid=user_guid))

    async def get_me(self) -> UserInfo:
        user_guid = await self.storage.user_guid()
        if not user_guid:
            raise AuthError("No authenticated user_guid is available in the current session")
        return await self.get_user_info(user_guid)

    async def get_object_by_username(self, username: str) -> ObjectByUsername:
        return await self.invoke(GetObjectByUsername(username=username))

    async def get_avatars(self, object_guid: str) -> ChatAvatars:
        return await self.invoke(GetAvatars(object_guid=object_guid))

    async def get_chats_updates(self, state: Optional[int] = None) -> ChatsUpdates:
        if state is None:
            state = await self.storage.updates_state()
        if state is None:
            state = int(time.time())

        result = await self.invoke(GetChatsUpdates(state=state))
        if result.new_state is not None:
            await self.storage.set_updates_state(result.new_state)
        return result

    async def get_contacts(self, offset: int = 0, limit: int = 100) -> RawObject:
        return await self.invoke(GetContacts(offset=offset, limit=limit))

    async def get_chat(self, object_guid: str) -> RawObject:
        return await self.invoke(GetChat(object_guid=object_guid))

    async def get_messages(self, object_guid: str, offset: int = 0, limit: int = 20) -> RawObject:
        return await self.invoke(GetMessages(object_guid=object_guid, offset=offset, limit=limit))

    async def get_history(self, object_guid: str, offset: int = 0, limit: int = 50) -> RawObject:
        return await self.invoke(GetHistory(object_guid=object_guid, offset=offset, limit=limit))

    async def send_voice(
        self,
        object_guid: str,
        path: str | Path,
        *,
        rnd: Optional[str] = None,
        duration_ms: float | int = 0,
        mime: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> SentMessage:
        file_path = Path(path)
        resolved_duration_ms = self._resolve_voice_duration_ms(file_path, duration_ms)
        return await self._send_uploaded_media(
            object_guid=object_guid,
            path=file_path,
            rnd=rnd,
            mime=mime,
            media_type="Voice",
            progress=progress,
            progress_args=progress_args,
            extra_file_inline={"time": resolved_duration_ms},
        )

    async def send_music(
        self,
        object_guid: str,
        path: str | Path,
        *,
        duration_ms: float | int,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> SentMessage:
        return await self._send_uploaded_media(
            object_guid=object_guid,
            path=path,
            rnd=rnd,
            mime=mime,
            media_type="Music",
            progress=progress,
            progress_args=progress_args,
            extra_file_inline={"time": duration_ms},
        )

    async def send_video(
        self,
        object_guid: str,
        path: str | Path,
        *,
        duration_ms: float | int,
        width: int,
        height: int,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        text: Optional[str] = None,
        is_round: bool = False,
        is_spoil: bool = False,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> SentMessage:
        return await self._send_uploaded_media(
            object_guid=object_guid,
            path=path,
            rnd=rnd,
            mime=mime,
            media_type="Video",
            text=text,
            progress=progress,
            progress_args=progress_args,
            extra_file_inline={
                "time": duration_ms,
                "width": width,
                "height": height,
                "is_round": is_round,
                "is_spoil": is_spoil,
            },
        )

    async def download_file(
        self,
        file: Any,
        path: str | Path | None = None,
        *,
        in_memory: bool = False,
        file_name: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> bytes | Path:
        if self._download_transport is None:
            raise TransportError("Download transport is not initialized")

        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("Downloading files requires an authenticated session")

        target = self._resolve_download_target(file)
        target_name = file_name or getattr(target, "file_name", None) or f"file_{getattr(target, 'file_id', 'unknown')}"

        if in_memory:
            destination = None
        else:
            destination = self._resolve_download_destination(path, target_name)

        return await self._download_transport.download_file(
            auth=auth,
            file_id=getattr(target, "file_id"),
            dc_id=getattr(target, "dc_id"),
            access_hash_rec=getattr(target, "access_hash_rec"),
            file_size=self._coerce_download_size(getattr(target, "size", None)),
            path=destination,
            in_memory=in_memory,
            progress=progress,
            progress_args=progress_args,
        )

    async def edit_message(self, object_guid: str, message_id: str, text: str) -> RawObject:
        return await self.invoke(EditMessage(object_guid=object_guid, message_id=message_id, text=text))

    async def delete_message(self, object_guid: str, message_id: str) -> RawObject:
        return await self.invoke(DeleteMessage(object_guid=object_guid, message_id=message_id))

    async def block_user(self, object_guid: str) -> RawObject:
        return await self.invoke(BlockUser(object_guid=object_guid))

    async def unblock_user(self, object_guid: str) -> RawObject:
        return await self.invoke(UnblockUser(object_guid=object_guid))

    async def authorize(self) -> Authorization | dict[str, str]:
        if await self.storage.auth():
            user_guid = await self.storage.user_guid()
            if not user_guid:
                raise AuthError("Authenticated session is missing user_guid")
            return {"user_guid": user_guid}

        self._print_welcome()

        while True:
            phone_number = self._normalize_phone_number(
                (self.phone_number or await self._prompt("Enter phone number (example: 989121234567): ")).strip()
            )
            if not phone_number:
                continue

            try:
                sent_code = await self.send_code(phone_number)
            except RubikaError as e:
                print(self._format_authorize_error(e, stage="phone_number"))
                self.phone_number = None
                continue

            self.phone_number = phone_number
            send_type = getattr(sent_code, "send_type", "SMS")
            print(f"The confirmation code has been sent via {send_type}.")
            break

        phone_code_hash = getattr(sent_code, "phone_code_hash", None)
        if not phone_code_hash:
            raise AuthError("The server response did not include phone_code_hash")

        while True:
            phone_code = (self.phone_code or await self._prompt("Enter confirmation code: ")).strip()
            if not phone_code:
                self.phone_code = None
                continue

            try:
                signed_in = await self.sign_in(
                    phone_number=self.phone_number,
                    phone_code_hash=phone_code_hash,
                    phone_code=phone_code,
                )
            except RubikaError as e:
                print(self._format_authorize_error(e, stage="phone_code"))
                self.phone_code = None
                continue

            self.phone_code = phone_code
            if await self.storage.auth():
                return signed_in

            break

        print("The account is not registered yet.")

        while True:
            first_name = (self.first_name or await self._prompt("Enter first name: ")).strip()
            if not first_name:
                self.first_name = None
                continue

            last_name = (self.last_name or await self._prompt("Enter last name (empty to skip): ")).strip()

            try:
                signed_up = await self.sign_up(first_name=first_name, last_name=last_name)
            except RubikaError as e:
                print(str(e))
                self.first_name = None
                self.last_name = ""
                continue

            self.first_name = first_name
            self.last_name = last_name
            return signed_up

    async def invoke(self, method: RawMethod[ResultT]) -> ResultT:
        return await self._invoke_once(method, allow_register_retry=True)

    async def receive_socket_update(self, timeout: Optional[float] = None) -> SocketUpdates:
        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("Receiving socket updates requires an authenticated session")

        await self._ensure_socket_handshake()
        if self._socket_transport is None:
            raise TransportError("Socket transport is not initialized")

        while True:
            payload = await self._socket_transport.recv(timeout=timeout)
            status = payload.get("status")
            if status == "OK" and "data_enc" not in payload:
                continue

            if payload.get("type") == "messenger" and "data_enc" in payload:
                decrypted = self._decrypt_response({"data_enc": payload["data_enc"]}, auth)
                return SocketUpdates._parse(self, decrypted)

            raise DecodeError(f"Unexpected socket payload shape: {payload}")

    async def _ensure_update_listener(self) -> None:
        if self._update_listener_task is not None and not self._update_listener_task.done():
            return
        if not self.enable_socket_handshake:
            return
        if not await self.storage.auth():
            return
        self._idle_event.clear()
        self._update_listener_task = asyncio.create_task(
            self._update_listener_loop(),
            name="rubigram-update-listener",
        )

    async def _update_listener_loop(self) -> None:
        try:
            while self._is_connected:
                try:
                    update = await self.receive_socket_update()
                    await self._dispatch_socket_update(update)
                except asyncio.CancelledError:
                    raise
                except (TransportError, NetworkError, DecodeError) as exc:
                    log.warning("Update listener recovered after socket/read error: %s", exc)
                    await asyncio.sleep(1)
                    continue
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Update listener stopped because of an exception")
        finally:
            self._idle_event.set()

    async def _dispatch_socket_update(self, update: SocketUpdates) -> None:
        if not self._message_handlers:
            return

        for message_update in update.message_updates:
            message = message_update.message
            if message is None:
                continue

            for handler in list(self._message_handlers):
                try:
                    passed = handler.filter(self, message)
                    if inspect.isawaitable(passed):
                        passed = await passed
                    if not passed:
                        continue

                    result = handler.callback(self, message)
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    log.exception("Message handler failed")

    async def _invoke_once(self, method: RawMethod[ResultT], allow_register_retry: bool) -> ResultT:
        if not self._is_connected or self._transport is None or self._codec is None or self._pool is None:
            raise AuthError("Client not started. Call start() first.")
        if not isinstance(method, RawMethod):
            raise TypeError("invoke() expects a RawMethod instance")

        request_key = await self._resolve_request_key(method)
        if method.auth_mode == "auth":
            await self._ensure_socket_handshake()
            if method.name != "registerDevice":
                await self._ensure_registered_device()
        if method.auth_mode == "tmp" and method.name in {"signIn", "signUp"} and getattr(method, "public_key", None) is None:
            public_key = await self.storage.public_key()
            if not public_key:
                raise AuthError("Public key is missing for login flow")
            setattr(method, "public_key", public_key)
        data_object = self._build_data_object(method)
        if method.auth_mode == "tmp":
            payload = self._codec.build_tmp_payload(
                api_version=await self.storage.api_version(),
                tmp_session=request_key,
                data_obj=data_object,
            )
        else:
            payload = self._codec.build_payload(
                api_version=await self.storage.api_version(),
                auth=request_key,
                data_obj=data_object,
            )

        response = await self._transport.send_payload(payload)
        await self.storage.set_api_url(self._pool.get_current())
        self._raise_if_not_ok(response)

        if method.auth_mode == "tmp":
            data = self._decrypt_tmp_response(response, request_key)
        else:
            data = self._decrypt_response(response, request_key)
            try:
                self._raise_if_not_ok(data, raw=response)
            except RegisterDeviceRequired:
                if allow_register_retry and method.name != "registerDevice":
                    await self.register_device(force=True)
                    return await self._invoke_once(method, allow_register_retry=False)
                raise

        result = data.get("data", data) if isinstance(data, dict) else data

        if method.unwrap_auth_on_success and isinstance(result, dict) and "auth" in result:
            await self._finalize_login(result["auth"], result)

        return method.parse_response(self, result)

    async def _send_uploaded_media(
        self,
        *,
        object_guid: str,
        path: str | Path,
        media_type: str,
        rnd: Optional[str] = None,
        mime: Optional[str] = None,
        text: Optional[str] = None,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
        extra_file_inline: Optional[Dict[str, Any]] = None,
    ) -> SentMessage:
        file_path = Path(path)
        file_name = file_path.name
        file_size = file_path.stat().st_size
        file_mime = mime or self._guess_upload_mime(file_path)
        descriptor = await self.request_send_file(file_name=file_name, size=file_size, mime=file_mime)
        uploaded = await self._upload_file(
            path=file_path,
            descriptor=descriptor,
            progress=progress,
            progress_args=progress_args,
        )

        file_inline: Dict[str, Any] = {
            "file_name": file_name,
            "size": file_size,
            "type": media_type,
            "dc_id": uploaded.dc_id,
            "file_id": uploaded.id,
            "mime": file_mime,
            "access_hash_rec": uploaded.access_hash_rec,
        }
        if extra_file_inline:
            file_inline.update(extra_file_inline)

        return await self.send_message(
            object_guid=object_guid,
            rnd=rnd or str(time.time_ns()),
            text=text,
            file_inline=file_inline,
        )

    async def _upload_file(
        self,
        *,
        path: str | Path,
        descriptor: UploadDescriptor,
        progress: Optional[Callable[..., Any]] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> UploadDescriptor:
        if self._upload_transport is None:
            raise TransportError("Upload transport is not initialized")
        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("Uploading files requires an authenticated session")
        return await self._upload_transport.upload_file(
            auth=auth,
            descriptor=descriptor,
            path=path,
            progress=progress,
            progress_args=progress_args,
        )

    def _build_message_metadata(
        self,
        text: Optional[str],
        *,
        entities: Optional[Sequence[MessageEntity]],
        parse_mode: Optional[str | ParseMode],
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        if text is None:
            if entities:
                raise ValueError("entities require a text message")
            return None, None

        if entities and parse_mode is not None:
            raise ValueError("Use either entities or parse_mode, not both")

        if entities:
            return text, self._metadata_from_entities(entities)

        if parse_mode is None:
            return text, None

        normalized = self._normalize_parse_mode(parse_mode)
        if normalized == ParseMode.MARKDOWN:
            return self._parse_markdown_entities(text)
        if normalized == ParseMode.HTML:
            return self._parse_html_entities(text)
        return text, None

    def _normalize_parse_mode(self, parse_mode: str | ParseMode) -> ParseMode:
        if isinstance(parse_mode, ParseMode):
            return parse_mode
        value = str(parse_mode).strip().lower()
        if value in {"markdown", "md"}:
            return ParseMode.MARKDOWN
        if value == "html":
            return ParseMode.HTML
        if value in {"default", "none"}:
            return ParseMode.DEFAULT
        raise ValueError(f"Unsupported parse_mode: {parse_mode}")

    def _metadata_from_entities(self, entities: Sequence[MessageEntity]) -> Optional[Dict[str, Any]]:
        if not entities:
            return None
        return {"meta_data_parts": [entity.to_metadata_part() for entity in entities]}

    def _parse_markdown_entities(self, text: str) -> tuple[str, Optional[Dict[str, Any]]]:
        pattern = re.compile(r"\*\*(.+?)\*\*")
        return self._extract_entities_from_pattern(text, pattern, lambda match: MessageEntity.bold(match[0], match[1]))

    def _parse_html_entities(self, text: str) -> tuple[str, Optional[Dict[str, Any]]]:
        pattern = re.compile(r"<(b|strong)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
        return self._extract_entities_from_pattern(text, pattern, lambda match: MessageEntity.bold(match[0], match[1]))

    def _extract_entities_from_pattern(
        self,
        text: str,
        pattern: re.Pattern[str],
        entity_builder: Callable[[tuple[int, int]], MessageEntity],
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        entities: list[MessageEntity] = []
        parts: list[str] = []
        cursor = 0
        plain_length = 0

        for match in pattern.finditer(text):
            start, end = match.span()
            parts.append(text[cursor:start])
            plain_length += len(text[cursor:start])
            inner_text = match.group(match.lastindex or 1)
            parts.append(inner_text)
            entities.append(entity_builder((plain_length, len(inner_text))))
            plain_length += len(inner_text)
            cursor = end

        parts.append(text[cursor:])
        plain_text = "".join(parts)
        return plain_text, self._metadata_from_entities(entities)

    def _resolve_download_target(self, file: Any) -> Any:
        if hasattr(file, "file_id") and hasattr(file, "dc_id") and hasattr(file, "access_hash_rec"):
            return file

        if getattr(file, "file_inline", None) is not None:
            return file.file_inline

        if getattr(file, "sticker", None) is not None and getattr(file.sticker, "file", None) is not None:
            return file.sticker.file

        raise ValueError("The provided object does not contain downloadable file metadata")

    def _resolve_download_destination(self, path: str | Path | None, file_name: str) -> Path:
        if path is None:
            return Path(file_name)

        destination = Path(path)
        if destination.exists() and destination.is_dir():
            return destination / file_name
        if str(path).endswith(("/", "\\\\")):
            return destination / file_name
        if destination.suffix:
            return destination
        return destination / file_name

    def _coerce_download_size(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _guess_upload_mime(self, path: Path) -> str:
        guessed, _ = mimetypes.guess_type(path.name)
        if guessed:
            suffix = path.suffix.lower().lstrip(".")
            if suffix in {"ogg", "mp4", "jpg", "jpeg", "png", "zip", "mp3"}:
                return "jpg" if suffix == "jpeg" else suffix
            return guessed
        suffix = path.suffix.lower().lstrip(".")
        return suffix or "bin"

    def _resolve_voice_duration_ms(self, path: Path, duration_ms: float | int) -> float | int:
        try:
            if float(duration_ms) > 0:
                return duration_ms
        except (TypeError, ValueError):
            pass

        if path.suffix.lower() == ".ogg":
            parsed = self._parse_ogg_opus_duration_ms(path)
            if parsed > 0:
                return parsed

        raise ValueError(
            "Voice duration could not be determined from the file. "
            "Pass duration_ms explicitly."
        )

    def _parse_ogg_opus_duration_ms(self, path: Path) -> float:
        data = path.read_bytes()
        offset = 0
        pre_skip = 0
        found_opus_head = False
        last_granule_position: Optional[int] = None

        while offset + 27 <= len(data):
            capture = data[offset:offset + 4]
            if capture != b"OggS":
                next_offset = data.find(b"OggS", offset + 1)
                if next_offset < 0:
                    break
                offset = next_offset
                continue

            page_segments = data[offset + 26]
            header_size = 27 + page_segments
            if offset + header_size > len(data):
                break

            segment_table = data[offset + 27:offset + header_size]
            payload_size = sum(segment_table)
            page_end = offset + header_size + payload_size
            if page_end > len(data):
                break

            granule_position = int.from_bytes(data[offset + 6:offset + 14], "little", signed=False)
            if granule_position:
                last_granule_position = granule_position

            payload = data[offset + header_size:page_end]
            payload_offset = 0
            packet = bytearray()

            for segment_length in segment_table:
                packet.extend(payload[payload_offset:payload_offset + segment_length])
                payload_offset += segment_length

                if segment_length < 255:
                    if not found_opus_head and packet.startswith(b"OpusHead") and len(packet) >= 12:
                        pre_skip = int.from_bytes(packet[10:12], "little", signed=False)
                        found_opus_head = True
                    packet.clear()

            offset = page_end

        if not found_opus_head or last_granule_position is None:
            return 0.0

        duration_ms = max(0, last_granule_position - pre_skip) * 1000.0 / 48000.0
        return round(duration_ms, 3)

    def _build_data_object(self, method: RawMethod) -> dict[str, Any]:
        input_data = method.to_input()
        if method.auth_mode == "tmp" and method.name in {"signIn", "signUp"} and "public_key" not in input_data:
            raise AuthError("Public key is missing for login flow")

        return {
            "method": method.name,
            "input": input_data,
            "client": self.device_info,
        }

    async def _resolve_request_key(self, method: RawMethod) -> str:
        if method.auth_mode == "tmp":
            tmp_session = await self.storage.tmp_session()
            if tmp_session is None:
                tmp_session = generate_tmp_session()
                await self.storage.set_tmp_session(tmp_session)
            await self._ensure_login_key_pair()
            return tmp_session

        auth = await self.storage.auth()
        if not auth:
            raise LoginRequired("This method requires an authenticated session")
        return auth

    def _decrypt_response(self, response: dict[str, Any], request_key: str) -> dict[str, Any]:
        assert self._codec is not None

        try:
            return self._codec.decrypt_response(response, request_key)
        except Exception as e:
            raise DecodeError(f"Failed to decrypt response: {e}") from e

    def _decrypt_tmp_response(self, response: dict[str, Any], tmp_session: str) -> dict[str, Any]:
        data = self._decrypt_response(response, tmp_session)
        self._raise_if_not_ok(data, raw=response)
        return data

    async def _finalize_login(self, encrypted_auth: str, data: dict[str, Any]) -> None:
        assert self._codec is not None

        try:
            auth = self._codec.unwrap_server_auth(encrypted_auth)
        except Exception as e:
            raise DecodeError(f"Failed to unwrap server auth: {e}") from e

        await self.storage.set_auth(auth)
        await self.storage.set_tmp_session(None)
        await self.storage.set_registered_device(False)
        await self.storage.set_registered_device_version(None)

        user_guid = data.get("user_guid")
        if not user_guid:
            user = data.get("user")
            if isinstance(user, dict):
                user_guid = user.get("user_guid")

        if user_guid:
            await self.storage.set_user_guid(user_guid)

        await self._ensure_socket_handshake(force_reconnect=True)
        await self._ensure_registered_device(force=True)

    async def _ensure_login_key_pair(self) -> None:
        public_key = await self.storage.public_key()
        private_key_pem = await self.storage.private_key_pem()
        if public_key and private_key_pem:
            expected_public_key = export_public_key_for_login(private_key_pem)
            if public_key == expected_public_key:
                return
            await self.storage.set_public_key(expected_public_key)
            return
        if private_key_pem:
            await self.storage.set_public_key(export_public_key_for_login(private_key_pem))
            return

        if self.pem_private_key:
            private_key_pem = self.pem_private_key
            public_key = export_public_key_for_login(private_key_pem)
        else:
            public_key, private_key_pem = generate_rsa_key_pair()

        await self.storage.set_public_key(public_key)
        await self.storage.set_private_key_pem(private_key_pem)

    async def _ensure_socket_handshake(self, force_reconnect: bool = False) -> None:
        if not self.enable_socket_handshake:
            return

        auth = await self.storage.auth()
        if not auth:
            return

        socket_urls = await self._build_socket_urls()
        if self._socket_transport is None:
            self._socket_transport = SocketTransport(
                socket_urls,
                timeout=self.timeout,
                heartbeat_interval=self.socket_heartbeat_interval,
            )
        elif force_reconnect:
            await self._socket_transport.close()
            self._socket_transport = SocketTransport(
                socket_urls,
                timeout=self.timeout,
                heartbeat_interval=self.socket_heartbeat_interval,
            )

        await self._socket_transport.handshake(
            auth=auth,
            api_version=self.SOCKET_HANDSHAKE_API_VERSION,
            force_reconnect=force_reconnect,
        )

    async def _ensure_registered_device(self, force: bool = False) -> None:
        if not self.enable_register_device:
            return

        auth = await self.storage.auth()
        if not auth:
            return

        if not force:
            if await self.storage.registered_device() and await self.storage.registered_device_version() == self.APP_VERSION:
                return

        await self.register_device(force=True)

    async def _ensure_device_hash(self) -> str:
        stored_hash = await self.storage.device_hash()
        device_hash = self.device_hash or stored_hash
        if not device_hash:
            device_hash = generate_device_hash()

        if device_hash != stored_hash:
            await self.storage.set_device_hash(device_hash)

        self.device_hash = device_hash
        return device_hash

    def _register_device_app_version(self) -> str:
        return f"{self.REGISTER_DEVICE_APP_VERSION_PREFIX}{self.APP_VERSION}"

    async def _build_socket_urls(self) -> list[str]:
        discovered_urls = await self.storage.sockets() or []
        configured_urls = list(self.socket_urls)

        urls: list[str] = []
        for url in [*discovered_urls, *configured_urls]:
            if url and url not in urls:
                urls.append(url)
        return urls

    def _raise_if_not_ok(self, payload: dict[str, Any], raw: Optional[dict[str, Any]] = None) -> None:
        status = payload.get("status")
        status_det = payload.get("status_det")
        if status and status != "OK":
            error = map_rpc_error(status, status_det, raw or payload)
            raise error

    def _should_interactive_authorize(self) -> bool:
        if not self.interactive_auth:
            return False
        if sys.stdin is None or sys.stdout is None:
            return False
        return bool(getattr(sys.stdin, "isatty", lambda: False)() and getattr(sys.stdout, "isatty", lambda: False)())

    def _print_welcome(self) -> None:
        print(f"Welcome to Rubigram (version {__version__})")
        print("No saved session was found. Starting interactive authorization.")
        print("Phone format: use international format without '+' or leading zero. Example: 989121234567\n")

    async def _prompt(self, text: str) -> str:
        return await asyncio.to_thread(input, text)

    def _normalize_phone_number(self, phone_number: str) -> str:
        normalized = "".join(ch for ch in phone_number if ch.isdigit() or ch == "+").strip()
        if normalized.startswith("+"):
            normalized = normalized[1:]
        if normalized.startswith("0098"):
            normalized = "98" + normalized[4:]
        elif normalized.startswith("09"):
            normalized = "98" + normalized[1:]
        return normalized

    def _format_authorize_error(self, error: RubikaError, stage: str) -> str:
        if isinstance(error, InvalidInput) and stage == "phone_number":
            return (
                "The server rejected the phone number input. "
                "Use international format without '+' or leading zero. Example: 989121234567"
            )
        if isinstance(error, (CodeIsInvalid, PhoneCodeInvalid)) and stage == "phone_code":
            return "The confirmation code is invalid. Enter the latest SMS code exactly as received."
        if isinstance(error, PhoneHashInvalid) and stage == "phone_code":
            return "The confirmation session expired or phone_code_hash is invalid. Request a new code and try again."
        if isinstance(error, InvalidInput) and stage == "phone_code":
            return (
                "The server rejected the sign-in input (INVALID_INPUT). "
                "If the SMS code is correct, the likely causes are an expired phone_code_hash "
                "or an invalid login public_key/changeAuthType implementation."
            )
        return str(error)

    async def _safe_close(self) -> None:
        if self._update_listener_task is not None:
            self._update_listener_task.cancel()
            try:
                await self._update_listener_task
            except asyncio.CancelledError:
                pass
            self._update_listener_task = None
        self._idle_event.set()

        if self._socket_transport is not None:
            await self._socket_transport.close()
            self._socket_transport = None

        if self._transport is not None:
            await self._transport.close()
            self._transport = None

        if self._upload_transport is not None:
            await self._upload_transport.close()
            self._upload_transport = None

        if self._dc_discovery is not None:
            await self._dc_discovery.close()
            self._dc_discovery = None

        await self.storage.close()
        self._pool = None
        self._codec = None
        self._is_connected = False
