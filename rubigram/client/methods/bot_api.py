"""Bot API (``Client(token=...)``) methods over ``botapi.rubika.ir``."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Union

from rubigram.errors import InvalidInput, RubigramError
from rubigram.types.bot import Bot, BotCommand, BotUpdates, Chat, File, Keypad, SentMessage, WebhookUpdate

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _clean(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


class BotApi:
    async def _bot_call(self: "Client", method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        transport = self._require_bot(f"Bot API method {method}")
        try:
            return await transport.call(method, _clean(payload or {}))
        except InvalidInput as exc:
            if method == "sendMessage" and payload and str(payload.get("chat_id", "")).startswith("u0"):
                raise InvalidInput(exc.status, exc.status_det, exc.raw, method=method, client_show_message="Bot sendMessage expects chat_id (from get_updates()/webhooks/get_chat()), not a user_guid") from exc
            raise

    # Old private name used by rubigram 0.1.
    async def _invoke_bot(self: "Client", method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return await self._bot_call(method, payload)

    # -- helpers used by the shared methods --------------------------------------

    async def _bot_get_me(self: "Client") -> Bot:
        data = await self._bot_call("getMe")
        if isinstance(data, dict) and "bot" in data:
            data = data["bot"]
        return Bot._parse(self, data)

    async def _bot_get_chat(self: "Client", chat_id: str) -> Chat:
        data = await self._bot_call("getChat", {"chat_id": chat_id})
        if isinstance(data, dict) and "chat" in data:
            data = data["chat"]
        return Chat._parse(self, data)

    async def _bot_send_message(self: "Client", *, chat_id: str, text: str, chat_keypad: Any = None, inline_keypad: Any = None, chat_keypad_type: Any = None, disable_notification: bool = False, reply_to_message_id: Optional[str] = None) -> SentMessage:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "chat_keypad": _serialize(chat_keypad),
            "disable_notification": disable_notification,
            "inline_keypad": _serialize(inline_keypad),
            "reply_to_message_id": str(reply_to_message_id) if reply_to_message_id else None,
            "chat_keypad_type": str(getattr(chat_keypad_type, "value", chat_keypad_type)) if chat_keypad_type is not None else None,
        }
        return SentMessage._parse(self, await self._bot_call("sendMessage", payload))

    async def _bot_send_location(self: "Client", chat_id: str, latitude: str, longitude: str, *, reply_to_message_id: Optional[str] = None, chat_keypad: Any = None, inline_keypad: Any = None, chat_keypad_type: Any = None, disable_notification: bool = False) -> SentMessage:
        payload = {
            "chat_id": chat_id,
            "latitude": latitude,
            "longitude": longitude,
            "chat_keypad": _serialize(chat_keypad),
            "inline_keypad": _serialize(inline_keypad),
            "reply_to_message_id": reply_to_message_id,
            "disable_notification": disable_notification,
            "chat_keypad_type": str(getattr(chat_keypad_type, "value", chat_keypad_type)) if chat_keypad_type is not None else None,
        }
        return SentMessage._parse(self, await self._bot_call("sendLocation", payload))

    async def _bot_send_poll(self: "Client", chat_id: str, question: str, options: list[str]) -> SentMessage:
        return SentMessage._parse(self, await self._bot_call("sendPoll", {"chat_id": chat_id, "question": question, "options": options}))

    async def _bot_forward_message(self: "Client", from_chat_id: str, message_id: str, to_chat_id: str, *, disable_notification: bool = False) -> SentMessage:
        return SentMessage._parse(self, await self._bot_call("forwardMessage", {"from_chat_id": from_chat_id, "message_id": message_id, "to_chat_id": to_chat_id, "disable_notification": disable_notification}))

    async def _bot_edit_message_text(self: "Client", chat_id: str, message_id: str, text: str) -> SentMessage:
        return SentMessage._parse(self, await self._bot_call("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text}))

    async def _bot_delete_message(self: "Client", chat_id: str, message_id: str) -> bool:
        await self._bot_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
        return True

    async def _bot_request_send_file(self: "Client", file_type: str) -> Dict[str, Any]:
        data = await self._bot_call("requestSendFile", {"type": file_type})
        if not isinstance(data, dict):
            raise RubigramError("requestSendFile returned an unexpected payload")
        return data

    async def _bot_send_media(self: "Client", chat_id: str, path: Union[str, Path], *, file_type: str, text: Optional[str] = None, reply_to_message_id: Optional[str] = None, **kwargs: Any) -> SentMessage:
        descriptor = await self._bot_request_send_file(file_type)
        upload_url = descriptor.get("upload_url")
        if not upload_url:
            raise RubigramError("requestSendFile did not return upload_url")
        file_id = await self.upload_bot_file(upload_url, path)
        return await self.send_file(chat_id, file_id, text=text, reply_to_message_id=reply_to_message_id, **kwargs)

    # -- public Bot API methods ---------------------------------------------------------

    async def get_bot_updates(self: "Client", offset_id: Optional[str] = None, limit: Optional[int] = None) -> BotUpdates:
        """``getUpdates`` (long polling); the offset is persisted in the session. [bot]"""
        payload = _clean({"offset_id": offset_id or self._bot_last_offset_id, "limit": limit or getattr(self, "_bot_poll_limit", None)})
        result = BotUpdates._parse(self, await self._bot_call("getUpdates", payload))
        if result.next_offset_id is not None:
            self._bot_last_offset_id = result.next_offset_id
            await self.storage.set_bot_offset_id(result.next_offset_id)
        return result

    async def send_contact(self: "Client", chat_id: Any, first_name: str, last_name: str, phone_number: str, *, chat_keypad: Any = None, inline_keypad: Any = None, reply_to_message_id: Optional[str] = None, disable_notification: bool = False, chat_keypad_type: Any = None) -> SentMessage:
        """``sendContact``. [bot]"""
        payload = {
            "chat_id": self._resolve_object_guid(chat_id),
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "chat_keypad": _serialize(chat_keypad),
            "inline_keypad": _serialize(inline_keypad),
            "reply_to_message_id": reply_to_message_id,
            "disable_notification": disable_notification,
            "chat_keypad_type": str(getattr(chat_keypad_type, "value", chat_keypad_type)) if chat_keypad_type is not None else None,
        }
        return SentMessage._parse(self, await self._bot_call("sendContact", payload))

    async def edit_message_text(self: "Client", chat_id: Any, message_id: Any, text: str) -> Any:
        """``editMessageText`` (user sessions fall back to :meth:`edit_message`). [HTTP][bot]"""
        if not self.is_bot:
            return await self.edit_message(chat_id, message_id, text)
        return await self._bot_edit_message_text(self._resolve_object_guid(chat_id), str(message_id), text)

    async def edit_message_keypad(self: "Client", chat_id: Any, message_id: Any, inline_keypad: Keypad) -> bool:
        """``editMessageKeypad``. [bot]"""
        await self._bot_call("editMessageKeypad", {"chat_id": self._resolve_object_guid(chat_id), "message_id": str(message_id), "inline_keypad": _serialize(inline_keypad)})
        return True

    edit_inline_keypad = edit_message_keypad

    async def set_commands(self: "Client", bot_commands: Sequence[Union[BotCommand, Dict[str, Any]]]) -> bool:
        """``setCommands``. [bot]"""
        await self._bot_call("setCommands", {"bot_commands": [_serialize(command) for command in bot_commands]})
        return True

    async def update_bot_endpoints(self: "Client", url: str, type: str) -> bool:
        """``updateBotEndpoints`` (webhook registration). [bot]"""
        await self._bot_call("updateBotEndpoints", {"url": url, "type": str(getattr(type, "value", type))})
        return True

    async def edit_chat_keypad(self: "Client", chat_id: Any, *, chat_keypad_type: Any, chat_keypad: Optional[Keypad] = None) -> bool:
        """``editChatKeypad``. [bot]"""
        await self._bot_call("editChatKeypad", {"chat_id": self._resolve_object_guid(chat_id), "chat_keypad_type": str(getattr(chat_keypad_type, "value", chat_keypad_type)), "chat_keypad": _serialize(chat_keypad)})
        return True

    async def get_file(self: "Client", file_id: str) -> File:
        """``getFile`` (returns ``download_url``). [bot]"""
        data = await self._bot_call("getFile", {"file_id": file_id})
        if isinstance(data, dict) and "file" in data:
            data = data["file"]
        return File._parse(self, data)

    async def download_bot_file(self: "Client", file: Any, path: Union[str, Path, None] = None, *, in_memory: bool = False, file_name: Optional[str] = None) -> Union[bytes, Path]:
        """Download a Bot API file (``getFile`` + ``download_url``). [bot]"""
        transport = self._require_bot("download_bot_file")
        url = getattr(file, "download_url", None) if not isinstance(file, str) else None
        if not url:
            file_id = file if isinstance(file, str) else getattr(file, "file_id", None)
            if not file_id:
                raise ValueError("download_bot_file() needs a file_id or a File with download_url")
            fetched = await self.get_file(str(file_id))
            url = fetched.download_url
            file = fetched
        if not url:
            raise RubigramError("getFile did not return download_url")
        if in_memory:
            return await transport.download_file(url, in_memory=True)
        name = file_name or getattr(file, "file_name", None) or self._default_file_name_from_url(url)
        return await transport.download_file(url, path=self._resolve_download_destination(path, name))

    async def upload_bot_file(self: "Client", upload_url: str, path: Union[str, Path]) -> str:
        """Upload to the URL returned by ``requestSendFile`` and return the ``file_id``. [bot]"""
        transport = self._require_bot("upload_bot_file")
        payload = await transport.upload_file(upload_url, path)
        data = transport.unwrap(payload, method="uploadFile")
        if isinstance(data, dict) and data.get("file_id"):
            return str(data["file_id"])
        if isinstance(data, str):
            return data
        raise RubigramError("Upload response did not include file_id")

    async def send_file(self: "Client", chat_id: Any, file_id: str, *, text: Optional[str] = None, reply_to_message_id: Optional[str] = None, disable_notification: bool = False, chat_keypad: Any = None, inline_keypad: Any = None, chat_keypad_type: Any = None) -> SentMessage:
        """``sendFile`` with an uploaded ``file_id``. [bot]"""
        payload = {
            "chat_id": self._resolve_object_guid(chat_id),
            "file_id": file_id,
            "text": text,
            "reply_to_message_id": reply_to_message_id,
            "disable_notification": disable_notification,
            "chat_keypad": _serialize(chat_keypad),
            "inline_keypad": _serialize(inline_keypad),
            "chat_keypad_type": str(getattr(chat_keypad_type, "value", chat_keypad_type)) if chat_keypad_type is not None else None,
        }
        return SentMessage._parse(self, await self._bot_call("sendFile", payload))

    async def ban_chat_member(self: "Client", chat_id: Any, user_id: str) -> bool:
        """``banChatMember``. [bot]"""
        await self._bot_call("banChatMember", {"chat_id": self._resolve_object_guid(chat_id), "user_id": user_id})
        return True

    async def unban_chat_member(self: "Client", chat_id: Any, user_id: str) -> bool:
        """``unbanChatMember``. [bot]"""
        await self._bot_call("unbanChatMember", {"chat_id": self._resolve_object_guid(chat_id), "user_id": user_id})
        return True

    async def parse_webhook_update(self: "Client", payload: Dict[str, Any]) -> WebhookUpdate:
        """Parse a webhook body into typed objects (no network). [bot]"""
        return WebhookUpdate._parse(self, payload)

    async def dispatch_webhook_update(self: "Client", payload: Dict[str, Any]) -> WebhookUpdate:
        """Parse a webhook body and run the registered handlers. [bot]"""
        update = await self.parse_webhook_update(payload)
        if update.update is not None:
            await self._dispatcher.dispatch_bot_update(update.update)
        if update.inline_message is not None:
            await self._dispatcher.dispatch_inline_message(update.inline_message)
        return update


__all__ = ["BotApi"]
