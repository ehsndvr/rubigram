from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from rubigram.exceptions import RubikaError, map_rpc_error

from .enums import ChatKeypadType, FileType
from .transport import BotTransport
from .types import (
    Bot,
    BotCommand,
    BotUpdates,
    Chat,
    File,
    InlineMessage,
    Keypad,
    Message,
    SentMessage,
    Update,
    WebhookUpdate,
)


Handler = Callable[..., Any]


class _BoundHandler:
    def __init__(self, callback: Handler):
        self.callback = callback


class BotClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = BotTransport.DEFAULT_BASE_URL,
        timeout: float = BotTransport.DEFAULT_TIMEOUT,
    ):
        self.token = token
        self._transport = BotTransport(token, base_url=base_url, timeout=timeout)
        self._update_handlers: list[_BoundHandler] = []
        self._message_handlers: list[_BoundHandler] = []
        self._inline_handlers: list[_BoundHandler] = []
        self._polling_task: Optional[asyncio.Task[None]] = None
        self._polling_stop = asyncio.Event()
        self._last_offset_id: Optional[str] = None

    async def close(self) -> None:
        await self.stop_polling()
        await self._transport.close()

    async def __aenter__(self) -> "BotClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def on_update(self) -> Callable[[Handler], Handler]:
        def decorator(func: Handler) -> Handler:
            self._update_handlers.append(_BoundHandler(func))
            return func

        return decorator

    def on_message(self) -> Callable[[Handler], Handler]:
        def decorator(func: Handler) -> Handler:
            self._message_handlers.append(_BoundHandler(func))
            return func

        return decorator

    def on_inline_message(self) -> Callable[[Handler], Handler]:
        def decorator(func: Handler) -> Handler:
            self._inline_handlers.append(_BoundHandler(func))
            return func

        return decorator

    async def invoke(self, method: str, payload: Optional[dict[str, Any]] = None) -> Any:
        response = await self._transport.call_method(method, payload)
        return self._unwrap_response(response)

    def parse_webhook_update(self, payload: dict[str, Any]) -> WebhookUpdate:
        return WebhookUpdate._parse(self, payload)

    async def dispatch_webhook_update(self, payload: dict[str, Any]) -> WebhookUpdate:
        update = self.parse_webhook_update(payload)
        await self._dispatch_webhook_update(update)
        return update

    async def get_me(self) -> Bot:
        return Bot._parse(self, await self.invoke("getMe"))

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        chat_keypad: Optional[Keypad] = None,
        disable_notification: bool = False,
        inline_keypad: Optional[Keypad] = None,
        reply_to_message_id: Optional[str] = None,
        chat_keypad_type: Optional[ChatKeypadType | str] = None,
    ) -> SentMessage:
        payload = self._clean_payload(
            {
                "chat_id": chat_id,
                "text": text,
                "chat_keypad": self._serialize(chat_keypad),
                "disable_notification": disable_notification,
                "inline_keypad": self._serialize(inline_keypad),
                "reply_to_message_id": reply_to_message_id,
                "chat_keypad_type": str(chat_keypad_type) if chat_keypad_type is not None else None,
            }
        )
        return SentMessage._parse(self, await self.invoke("sendMessage", payload))

    async def send_poll(self, chat_id: str, question: str, options: list[str]) -> SentMessage:
        return SentMessage._parse(self, await self.invoke("sendPoll", {"chat_id": chat_id, "question": question, "options": options}))

    async def send_location(
        self,
        chat_id: str,
        latitude: str,
        longitude: str,
        *,
        chat_keypad: Optional[Keypad] = None,
        inline_keypad: Optional[Keypad] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad_type: Optional[ChatKeypadType | str] = None,
    ) -> SentMessage:
        payload = self._clean_payload(
            {
                "chat_id": chat_id,
                "latitude": latitude,
                "longitude": longitude,
                "chat_keypad": self._serialize(chat_keypad),
                "inline_keypad": self._serialize(inline_keypad),
                "reply_to_message_id": reply_to_message_id,
                "disable_notification": disable_notification,
                "chat_keypad_type": str(chat_keypad_type) if chat_keypad_type is not None else None,
            }
        )
        return SentMessage._parse(self, await self.invoke("sendLocation", payload))

    async def send_contact(
        self,
        chat_id: str,
        first_name: str,
        last_name: str,
        phone_number: str,
        *,
        chat_keypad: Optional[Keypad] = None,
        inline_keypad: Optional[Keypad] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad_type: Optional[ChatKeypadType | str] = None,
    ) -> SentMessage:
        payload = self._clean_payload(
            {
                "chat_id": chat_id,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "chat_keypad": self._serialize(chat_keypad),
                "inline_keypad": self._serialize(inline_keypad),
                "reply_to_message_id": reply_to_message_id,
                "disable_notification": disable_notification,
                "chat_keypad_type": str(chat_keypad_type) if chat_keypad_type is not None else None,
            }
        )
        return SentMessage._parse(self, await self.invoke("sendContact", payload))

    async def get_chat(self, chat_id: str) -> Chat:
        data = await self.invoke("getChat", {"chat_id": chat_id})
        return Chat._parse(self, data.get("chat") if isinstance(data, dict) and "chat" in data else data)

    async def get_updates(self, offset_id: Optional[str] = None, limit: Optional[int] = None) -> BotUpdates:
        payload = self._clean_payload({"offset_id": offset_id, "limit": limit})
        return BotUpdates._parse(self, await self.invoke("getUpdates", payload))

    async def forward_message(
        self,
        from_chat_id: str,
        message_id: str,
        to_chat_id: str,
        *,
        disable_notification: bool = False,
    ) -> SentMessage:
        payload = {
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "to_chat_id": to_chat_id,
            "disable_notification": disable_notification,
        }
        return SentMessage._parse(self, await self.invoke("forwardMessage", payload))

    async def edit_message_text(self, chat_id: str, message_id: str, text: str) -> SentMessage:
        return SentMessage._parse(self, await self.invoke("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text}))

    async def edit_message_keypad(self, chat_id: str, message_id: str, inline_keypad: Keypad) -> bool:
        payload = {"chat_id": chat_id, "message_id": message_id, "inline_keypad": self._serialize(inline_keypad)}
        await self.invoke("editMessageKeypad", payload)
        return True

    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        await self.invoke("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
        return True

    async def set_commands(self, bot_commands: list[BotCommand | dict[str, Any]]) -> bool:
        payload = {"bot_commands": [self._serialize(command) for command in bot_commands]}
        await self.invoke("setCommands", payload)
        return True

    async def update_bot_endpoints(self, url: str, type: str) -> bool:
        await self.invoke("updateBotEndpoints", {"url": url, "type": type})
        return True

    async def edit_chat_keypad(
        self,
        chat_id: str,
        *,
        chat_keypad_type: ChatKeypadType | str,
        chat_keypad: Optional[Keypad] = None,
    ) -> bool:
        payload = self._clean_payload(
            {
                "chat_id": chat_id,
                "chat_keypad_type": str(chat_keypad_type),
                "chat_keypad": self._serialize(chat_keypad),
            }
        )
        await self.invoke("editChatKeypad", payload)
        return True

    async def get_file(self, file_id: str) -> File:
        data = await self.invoke("getFile", {"file_id": file_id})
        return File._parse(self, data.get("file") if isinstance(data, dict) and "file" in data else data)

    async def request_send_file(self, type: FileType | str) -> dict[str, Any]:
        data = await self.invoke("requestSendFile", {"type": str(type)})
        if not isinstance(data, dict):
            raise RubikaError("requestSendFile returned an unexpected payload")
        return data

    async def upload_file(self, upload_url: str, path: str | Path) -> str:
        payload = await self._transport.upload_file(upload_url, str(path))
        data = self._unwrap_response(payload)
        if isinstance(data, dict):
            file_id = data.get("file_id")
            if file_id:
                return str(file_id)
        if isinstance(data, str):
            return data
        raise RubikaError("Upload response did not include file_id")

    async def send_file(
        self,
        chat_id: str,
        file_id: str,
        *,
        text: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad: Optional[Keypad] = None,
        inline_keypad: Optional[Keypad] = None,
        chat_keypad_type: Optional[ChatKeypadType | str] = None,
    ) -> SentMessage:
        payload = self._clean_payload(
            {
                "chat_id": chat_id,
                "file_id": file_id,
                "text": text,
                "reply_to_message_id": reply_to_message_id,
                "disable_notification": disable_notification,
                "chat_keypad": self._serialize(chat_keypad),
                "inline_keypad": self._serialize(inline_keypad),
                "chat_keypad_type": str(chat_keypad_type) if chat_keypad_type is not None else None,
            }
        )
        return SentMessage._parse(self, await self.invoke("sendFile", payload))

    async def send_media(
        self,
        chat_id: str,
        path: str | Path,
        *,
        type: FileType | str,
        text: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad: Optional[Keypad] = None,
        inline_keypad: Optional[Keypad] = None,
        chat_keypad_type: Optional[ChatKeypadType | str] = None,
    ) -> SentMessage:
        descriptor = await self.request_send_file(type)
        upload_url = descriptor.get("upload_url")
        if not upload_url:
            raise RubikaError("requestSendFile did not return upload_url")
        file_id = await self.upload_file(upload_url, path)
        return await self.send_file(
            chat_id,
            file_id,
            text=text,
            reply_to_message_id=reply_to_message_id,
            disable_notification=disable_notification,
            chat_keypad=chat_keypad,
            inline_keypad=inline_keypad,
            chat_keypad_type=chat_keypad_type,
        )

    async def send_photo(self, chat_id: str, path: str | Path, **kwargs: Any) -> SentMessage:
        return await self.send_media(chat_id, path, type=FileType.IMAGE, **kwargs)

    async def send_document(self, chat_id: str, path: str | Path, **kwargs: Any) -> SentMessage:
        return await self.send_media(chat_id, path, type=FileType.FILE, **kwargs)

    async def send_voice(self, chat_id: str, path: str | Path, **kwargs: Any) -> SentMessage:
        return await self.send_media(chat_id, path, type=FileType.VOICE, **kwargs)

    async def send_video(self, chat_id: str, path: str | Path, **kwargs: Any) -> SentMessage:
        return await self.send_media(chat_id, path, type=FileType.VIDEO, **kwargs)

    async def send_music(self, chat_id: str, path: str | Path, **kwargs: Any) -> SentMessage:
        return await self.send_media(chat_id, path, type=FileType.MUSIC, **kwargs)

    async def ban_chat_member(self, chat_id: str, user_id: str) -> bool:
        await self.invoke("banChatMember", {"chat_id": chat_id, "user_id": user_id})
        return True

    async def unban_chat_member(self, chat_id: str, user_id: str) -> bool:
        await self.invoke("unbanChatMember", {"chat_id": chat_id, "user_id": user_id})
        return True

    async def start_polling(self, *, limit: int = 100, idle_sleep: float = 1.0) -> None:
        if self._polling_task is not None and not self._polling_task.done():
            return
        self._polling_stop.clear()
        self._polling_task = asyncio.create_task(self._polling_loop(limit=limit, idle_sleep=idle_sleep))

    async def stop_polling(self) -> None:
        self._polling_stop.set()
        if self._polling_task is not None:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

    async def idle(self) -> None:
        if self._polling_task is None:
            raise RuntimeError("Polling has not been started")
        await self._polling_task

    async def _polling_loop(self, *, limit: int, idle_sleep: float) -> None:
        while not self._polling_stop.is_set():
            updates = await self.get_updates(offset_id=self._last_offset_id, limit=limit)
            if updates.next_offset_id:
                self._last_offset_id = updates.next_offset_id

            if not updates.updates:
                await asyncio.sleep(idle_sleep)
                continue

            for update in updates.updates:
                await self._dispatch_update(update)

    async def _dispatch_webhook_update(self, update: WebhookUpdate) -> None:
        if update.update is not None:
            await self._dispatch_update(update.update)
        if update.inline_message is not None:
            await self._dispatch_inline_message(update.inline_message)

    async def _dispatch_update(self, update: Update) -> None:
        for handler in list(self._update_handlers):
            await self._run_handler(handler.callback, self, update)

        if update.new_message is not None:
            await self._dispatch_message(update.new_message)

    async def _dispatch_message(self, message: Message) -> None:
        for handler in list(self._message_handlers):
            await self._run_handler(handler.callback, self, message)

    async def _dispatch_inline_message(self, inline_message: InlineMessage) -> None:
        for handler in list(self._inline_handlers):
            await self._run_handler(handler.callback, self, inline_message)

    async def _run_handler(self, callback: Handler, *args: Any) -> None:
        result = callback(*args)
        if inspect.isawaitable(result):
            await result

    def _unwrap_response(self, response: Any) -> Any:
        if not isinstance(response, dict):
            return response

        if "ok" in response:
            if response.get("ok") is False:
                description = response.get("description") or response.get("error")
                raise RubikaError(str(description or "Bot API request failed"))
            return response.get("result")

        status = response.get("status")
        if status and status != "OK":
            raise map_rpc_error(status, response.get("status_det"), response)

        if "data" in response:
            return response["data"]

        return response

    def _serialize(self, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if isinstance(value, list):
            return [self._serialize(item) for item in value]
        return value

    def _clean_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if value is not None}
