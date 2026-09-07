"""Storage abstraction shared by the SQLite file storage and the in-memory storage.

Every persisted value is declared once in :data:`FIELDS`; the concrete
storages only implement ``_get``/``_set`` plus open/close/delete.  The async
accessor methods (``auth()``, ``set_auth()`` …) are the public API used by
the client and the mixins.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from .session_codec import dump_session_string, load_session_string

DEFAULT_API_VERSION = "6"


@dataclass(frozen=True)
class Field:
    """A persisted session value.

    ``kind`` is ``text``, ``int``, ``bool`` or ``json``; ``column`` is the
    SQLite column name (kept compatible with the session files written by
    rubigram 0.1).
    """

    name: str
    kind: str
    column: str
    default: Any = None


FIELDS: tuple[Field, ...] = (
    Field("api_version", "text", "api_version", DEFAULT_API_VERSION),
    Field("api_url", "text", "api_url"),
    Field("api_urls", "json", "api_urls_json"),
    Field("suggested_urls", "json", "suggested_urls_json"),
    Field("storages", "json", "storages_json"),
    Field("cdn_urls", "json", "cdn_urls_json"),
    Field("sockets", "json", "sockets_json"),
    Field("dc_repository", "json", "dc_repository_json"),
    Field("auth", "text", "auth"),
    Field("tmp_session", "text", "tmp_session"),
    Field("public_key", "text", "public_key"),
    Field("private_key_pem", "text", "private_key_pem"),
    Field("user_guid", "text", "user_guid"),
    Field("updates_state", "int", "updates_state"),
    Field("contacts_state", "int", "contacts_state"),
    Field("folders_state", "int", "folders_state"),
    Field("chat_states", "json", "chat_states_json"),
    Field("device_hash", "text", "device_hash"),
    Field("registered_device", "bool", "registered_device", False),
    Field("registered_device_version", "text", "registered_device_version"),
    Field("bot_token", "text", "bot_token"),
    Field("bot_offset_id", "text", "bot_offset_id"),
)
FIELD_MAP: dict[str, Field] = {field.name: field for field in FIELDS}
SECRET_FIELDS = frozenset({"auth", "tmp_session", "private_key_pem", "bot_token"})


def encode_value(field: Field, value: Any) -> Any:
    """Convert a Python value to its stored representation."""
    if value is None:
        return None
    if field.kind == "json":
        return json.dumps(value, ensure_ascii=False)
    if field.kind == "bool":
        return 1 if value else 0
    if field.kind == "int":
        return int(value)
    return str(value)


def decode_value(field: Field, raw: Any) -> Any:
    """Convert a stored representation back to a Python value."""
    if raw is None:
        return field.default
    if field.kind == "json":
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            return field.default
    if field.kind == "bool":
        return bool(raw)
    if field.kind == "int":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return field.default
    return str(raw)


class Storage(ABC):
    """Async key/value session store with typed accessors."""

    def __init__(self, name: str):
        self.name = name

    # -- lifecycle ----------------------------------------------------------

    @abstractmethod
    async def open(self) -> None:
        """Open (and create/migrate) the underlying store."""

    @abstractmethod
    async def close(self) -> None:
        """Close the underlying store; the state must survive a later ``open``."""

    @abstractmethod
    async def delete(self) -> None:
        """Delete the persisted state, if any."""

    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    # -- generic access ----------------------------------------------------

    @abstractmethod
    def _get(self, field: Field) -> Any: ...

    @abstractmethod
    def _set(self, field: Field, value: Any) -> None: ...

    async def get(self, name: str) -> Any:
        return self._get(FIELD_MAP[name])

    async def set(self, name: str, value: Any) -> None:
        self._set(FIELD_MAP[name], value)

    # -- typed accessors ---------------------------------------------------

    async def api_version(self) -> str:
        return str(self._get(FIELD_MAP["api_version"]) or DEFAULT_API_VERSION)

    async def set_api_version(self, value: str) -> None:
        self._set(FIELD_MAP["api_version"], value)

    async def api_url(self) -> Optional[str]:
        return self._get(FIELD_MAP["api_url"])

    async def set_api_url(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["api_url"], value)

    async def api_urls(self) -> Optional[list[str]]:
        return self._get(FIELD_MAP["api_urls"])

    async def set_api_urls(self, value: Optional[list[str]]) -> None:
        self._set(FIELD_MAP["api_urls"], value)

    async def suggested_urls(self) -> Optional[dict[str, str]]:
        return self._get(FIELD_MAP["suggested_urls"])

    async def set_suggested_urls(self, value: Optional[dict[str, str]]) -> None:
        self._set(FIELD_MAP["suggested_urls"], value)

    async def storages(self) -> Optional[dict[str, Any]]:
        return self._get(FIELD_MAP["storages"])

    async def set_storages(self, value: Optional[dict[str, Any]]) -> None:
        self._set(FIELD_MAP["storages"], value)

    async def cdn_urls(self) -> Optional[dict[str, list[str]]]:
        return self._get(FIELD_MAP["cdn_urls"])

    async def set_cdn_urls(self, value: Optional[dict[str, list[str]]]) -> None:
        self._set(FIELD_MAP["cdn_urls"], value)

    async def sockets(self) -> Optional[list[str]]:
        return self._get(FIELD_MAP["sockets"])

    async def set_sockets(self, value: Optional[list[str]]) -> None:
        self._set(FIELD_MAP["sockets"], value)

    async def dc_repository(self) -> Optional[dict[str, Any]]:
        return self._get(FIELD_MAP["dc_repository"])

    async def set_dc_repository(self, value: Optional[dict[str, Any]]) -> None:
        self._set(FIELD_MAP["dc_repository"], value)

    async def auth(self) -> Optional[str]:
        return self._get(FIELD_MAP["auth"])

    async def set_auth(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["auth"], value)

    async def tmp_session(self) -> Optional[str]:
        return self._get(FIELD_MAP["tmp_session"])

    async def set_tmp_session(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["tmp_session"], value)

    async def public_key(self) -> Optional[str]:
        return self._get(FIELD_MAP["public_key"])

    async def set_public_key(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["public_key"], value)

    async def private_key_pem(self) -> Optional[str]:
        return self._get(FIELD_MAP["private_key_pem"])

    async def set_private_key_pem(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["private_key_pem"], value)

    async def user_guid(self) -> Optional[str]:
        return self._get(FIELD_MAP["user_guid"])

    async def set_user_guid(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["user_guid"], value)

    async def updates_state(self) -> Optional[int]:
        return self._get(FIELD_MAP["updates_state"])

    async def set_updates_state(self, value: Optional[int]) -> None:
        self._set(FIELD_MAP["updates_state"], value)

    async def contacts_state(self) -> Optional[int]:
        return self._get(FIELD_MAP["contacts_state"])

    async def set_contacts_state(self, value: Optional[int]) -> None:
        self._set(FIELD_MAP["contacts_state"], value)

    async def folders_state(self) -> Optional[int]:
        return self._get(FIELD_MAP["folders_state"])

    async def set_folders_state(self, value: Optional[int]) -> None:
        self._set(FIELD_MAP["folders_state"], value)

    async def chat_states(self) -> dict[str, Any]:
        return dict(self._get(FIELD_MAP["chat_states"]) or {})

    async def set_chat_states(self, value: Optional[dict[str, Any]]) -> None:
        self._set(FIELD_MAP["chat_states"], value)

    async def chat_state(self, object_guid: str) -> Optional[int]:
        value = (await self.chat_states()).get(object_guid)
        return int(value) if value is not None else None

    async def set_chat_state(self, object_guid: str, state: Optional[int]) -> None:
        states = await self.chat_states()
        if state is None:
            states.pop(object_guid, None)
        else:
            states[object_guid] = int(state)
        await self.set_chat_states(states)

    async def device_hash(self) -> Optional[str]:
        return self._get(FIELD_MAP["device_hash"])

    async def set_device_hash(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["device_hash"], value)

    async def registered_device(self) -> bool:
        return bool(self._get(FIELD_MAP["registered_device"]))

    async def set_registered_device(self, value: bool) -> None:
        self._set(FIELD_MAP["registered_device"], bool(value))

    async def registered_device_version(self) -> Optional[str]:
        return self._get(FIELD_MAP["registered_device_version"])

    async def set_registered_device_version(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["registered_device_version"], value)

    async def bot_token(self) -> Optional[str]:
        return self._get(FIELD_MAP["bot_token"])

    async def set_bot_token(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["bot_token"], value)

    async def bot_offset_id(self) -> Optional[str]:
        return self._get(FIELD_MAP["bot_offset_id"])

    async def set_bot_offset_id(self, value: Optional[str]) -> None:
        self._set(FIELD_MAP["bot_offset_id"], value)

    # -- bulk export / import --------------------------------------------

    async def export_session_dict(self) -> dict[str, Any]:
        """Every field as a plain dict (contains secrets; never log it)."""
        return {field.name: self._get(field) for field in FIELDS}

    async def import_session_dict(self, data: dict[str, Any]) -> None:
        for field in FIELDS:
            if field.name in data:
                value = data[field.name]
                if field.name == "api_version" and value is not None:
                    value = str(value)
                self._set(field, value)

    async def export_session_string(self) -> str:
        return dump_session_string(await self.export_session_dict())

    async def import_session_string(self, session_string: str) -> None:
        await self.import_session_dict(load_session_string(session_string))

    async def clear_auth(self) -> None:
        """Forget the login (auth, tmp session, user guid, device registration)."""
        for name in (
            "auth",
            "tmp_session",
            "user_guid",
            "registered_device_version",
            "updates_state",
            "chat_states",
            "contacts_state",
            "folders_state",
        ):
            self._set(FIELD_MAP[name], None)
        self._set(FIELD_MAP["registered_device"], False)


__all__ = ["DEFAULT_API_VERSION", "FIELDS", "FIELD_MAP", "SECRET_FIELDS", "Field", "Storage", "decode_value", "encode_value"]
