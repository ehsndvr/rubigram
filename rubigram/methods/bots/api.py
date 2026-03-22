from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import rubigram
from rubigram.bot.enums import ChatKeypadType as BotChatKeypadType, FileType as BotFileType
from rubigram.bot.types import BotCommand, File as BotFile, Keypad as BotKeypad, SentMessage as BotSentMessage
from rubigram.types import UploadDescriptor


class BotAPI:
    async def send_poll(self: "rubigram.Client", chat_id: str, question: str, options: list[str]) -> BotSentMessage:
        if not self.is_bot:
            raise RuntimeError("send_poll() is only available for token-based bot sessions")
        return BotSentMessage._parse(
            self,
            await self._invoke_bot("sendPoll", {"chat_id": chat_id, "question": question, "options": options}),
        )

    async def send_location(
        self: "rubigram.Client",
        chat_id: str,
        latitude: str,
        longitude: str,
        *,
        chat_keypad: Optional[BotKeypad] = None,
        inline_keypad: Optional[BotKeypad] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad_type: Optional[BotChatKeypadType | str] = None,
    ) -> BotSentMessage:
        if not self.is_bot:
            raise RuntimeError("send_location() is only available for token-based bot sessions")
        return BotSentMessage._parse(
            self,
            await self._invoke_bot(
                "sendLocation",
                self._clean_bot_payload(
                    {
                        "chat_id": chat_id,
                        "latitude": latitude,
                        "longitude": longitude,
                        "chat_keypad": self._serialize_bot(chat_keypad),
                        "inline_keypad": self._serialize_bot(inline_keypad),
                        "reply_to_message_id": reply_to_message_id,
                        "disable_notification": disable_notification,
                        "chat_keypad_type": str(chat_keypad_type) if chat_keypad_type is not None else None,
                    }
                ),
            ),
        )

    async def send_contact(
        self: "rubigram.Client",
        chat_id: str,
        first_name: str,
        last_name: str,
        phone_number: str,
        *,
        chat_keypad: Optional[BotKeypad] = None,
        inline_keypad: Optional[BotKeypad] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad_type: Optional[BotChatKeypadType | str] = None,
    ) -> BotSentMessage:
        if not self.is_bot:
            raise RuntimeError("send_contact() is only available for token-based bot sessions")
        return BotSentMessage._parse(
            self,
            await self._invoke_bot(
                "sendContact",
                self._clean_bot_payload(
                    {
                        "chat_id": chat_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone_number": phone_number,
                        "chat_keypad": self._serialize_bot(chat_keypad),
                        "inline_keypad": self._serialize_bot(inline_keypad),
                        "reply_to_message_id": reply_to_message_id,
                        "disable_notification": disable_notification,
                        "chat_keypad_type": str(chat_keypad_type) if chat_keypad_type is not None else None,
                    }
                ),
            ),
        )

    async def forward_message(
        self: "rubigram.Client",
        from_chat_id: str,
        message_id: str,
        to_chat_id: str,
        *,
        disable_notification: bool = False,
    ) -> BotSentMessage:
        if not self.is_bot:
            raise RuntimeError("forward_message() is only available for token-based bot sessions")
        return BotSentMessage._parse(
            self,
            await self._invoke_bot(
                "forwardMessage",
                {
                    "from_chat_id": from_chat_id,
                    "message_id": message_id,
                    "to_chat_id": to_chat_id,
                    "disable_notification": disable_notification,
                },
            ),
        )

    async def edit_message_keypad(self: "rubigram.Client", chat_id: str, message_id: str, inline_keypad: BotKeypad) -> bool:
        if not self.is_bot:
            raise RuntimeError("edit_message_keypad() is only available for token-based bot sessions")
        await self._invoke_bot(
            "editMessageKeypad",
            {"chat_id": chat_id, "message_id": message_id, "inline_keypad": self._serialize_bot(inline_keypad)},
        )
        return True

    async def edit_inline_keypad(self: "rubigram.Client", chat_id: str, message_id: str, inline_keypad: BotKeypad) -> bool:
        if not self.is_bot:
            raise RuntimeError("edit_inline_keypad() is only available for token-based bot sessions")
        return await self.edit_message_keypad(chat_id, message_id, inline_keypad)

    async def set_commands(self: "rubigram.Client", bot_commands: list[BotCommand | dict[str, Any]]) -> bool:
        if not self.is_bot:
            raise RuntimeError("set_commands() is only available for token-based bot sessions")
        await self._invoke_bot("setCommands", {"bot_commands": [self._serialize_bot(command) for command in bot_commands]})
        return True

    async def update_bot_endpoints(self: "rubigram.Client", url: str, type: str) -> bool:
        if not self.is_bot:
            raise RuntimeError("update_bot_endpoints() is only available for token-based bot sessions")
        await self._invoke_bot("updateBotEndpoints", {"url": url, "type": type})
        return True

    async def edit_chat_keypad(
        self: "rubigram.Client",
        chat_id: str,
        *,
        chat_keypad_type: BotChatKeypadType | str,
        chat_keypad: Optional[BotKeypad] = None,
    ) -> bool:
        if not self.is_bot:
            raise RuntimeError("edit_chat_keypad() is only available for token-based bot sessions")
        await self._invoke_bot(
            "editChatKeypad",
            self._clean_bot_payload(
                {
                    "chat_id": chat_id,
                    "chat_keypad_type": str(chat_keypad_type),
                    "chat_keypad": self._serialize_bot(chat_keypad),
                }
            ),
        )
        return True

    async def get_file(self: "rubigram.Client", file_id: str) -> BotFile:
        if not self.is_bot:
            raise RuntimeError("get_file() is only available for token-based bot sessions")
        data = await self._invoke_bot("getFile", {"file_id": file_id})
        if isinstance(data, dict) and "file" in data:
            data = data["file"]
        return BotFile._parse(self, data)

    async def upload_bot_file(self: "rubigram.Client", upload_url: str, path: str | Path) -> str:
        if not self.is_bot or self._bot_transport is None:
            raise RuntimeError("upload_bot_file() is only available for token-based bot sessions")
        payload = await self._bot_transport.upload_file(upload_url, str(path))
        data = self._unwrap_bot_response(payload)
        if isinstance(data, dict) and data.get("file_id"):
            return str(data["file_id"])
        if isinstance(data, str):
            return data
        from rubigram.exceptions import RubikaError

        raise RubikaError("Upload response did not include file_id")

    async def send_file(
        self: "rubigram.Client",
        chat_id: str,
        file_id: str,
        *,
        text: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad: Optional[BotKeypad] = None,
        inline_keypad: Optional[BotKeypad] = None,
        chat_keypad_type: Optional[BotChatKeypadType | str] = None,
    ) -> BotSentMessage:
        if not self.is_bot:
            raise RuntimeError("send_file() is only available for token-based bot sessions")
        return BotSentMessage._parse(
            self,
            await self._invoke_bot(
                "sendFile",
                self._clean_bot_payload(
                    {
                        "chat_id": chat_id,
                        "file_id": file_id,
                        "text": text,
                        "reply_to_message_id": reply_to_message_id,
                        "disable_notification": disable_notification,
                        "chat_keypad": self._serialize_bot(chat_keypad),
                        "inline_keypad": self._serialize_bot(inline_keypad),
                        "chat_keypad_type": str(chat_keypad_type) if chat_keypad_type is not None else None,
                    }
                ),
            ),
        )

    async def send_media(
        self: "rubigram.Client",
        chat_id: str,
        path: str | Path,
        *,
        type: BotFileType | str,
        text: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        disable_notification: bool = False,
        chat_keypad: Optional[BotKeypad] = None,
        inline_keypad: Optional[BotKeypad] = None,
        chat_keypad_type: Optional[BotChatKeypadType | str] = None,
    ) -> BotSentMessage:
        if not self.is_bot:
            raise RuntimeError("send_media() is only available for token-based bot sessions")
        descriptor = await self.request_send_file(type=type)
        upload_url = descriptor.get("upload_url") if isinstance(descriptor, dict) else None
        if not upload_url:
            from rubigram.exceptions import RubikaError

            raise RubikaError("requestSendFile did not return upload_url")
        file_id = await self.upload_bot_file(upload_url, path)
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

    async def ban_chat_member(self: "rubigram.Client", chat_id: str, user_id: str) -> bool:
        if not self.is_bot:
            raise RuntimeError("ban_chat_member() is only available for token-based bot sessions")
        await self._invoke_bot("banChatMember", {"chat_id": chat_id, "user_id": user_id})
        return True

    async def unban_chat_member(self: "rubigram.Client", chat_id: str, user_id: str) -> bool:
        if not self.is_bot:
            raise RuntimeError("unban_chat_member() is only available for token-based bot sessions")
        await self._invoke_bot("unbanChatMember", {"chat_id": chat_id, "user_id": user_id})
        return True

    async def upload_file(
        self: "rubigram.Client",
        *,
        path: str | Path,
        descriptor: UploadDescriptor | None = None,
        upload_url: str | None = None,
        progress: Optional[Any] = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        if self.is_bot:
            if upload_url is None:
                raise ValueError("Bot upload_file() requires upload_url")
            return await self.upload_bot_file(upload_url, path)
        if descriptor is None:
            raise ValueError("User upload_file() requires descriptor")
        return await self._upload_file(
            path=path,
            descriptor=descriptor,
            progress=progress,
            progress_args=progress_args,
        )
