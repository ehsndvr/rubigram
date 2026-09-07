"""Base class of every raw RPC method.

A raw method is a keyword dataclass whose fields are serialized to the RPC
``input`` automatically (``None`` values are dropped, enums become their
values, nested models become dicts).  Subclasses only declare::

    @dataclass
    class GetUserInfo(RawMethod[UserInfo]):
        user_guid: str

        method_name = "getUserInfo"
        result = UserInfo

Class attributes:

- ``method_name``: the Rubika RPC name.
- ``auth_mode``: ``"auth"`` (encrypted with the session auth), ``"tmp"``
  (login flow, encrypted with the temporary session) or ``"none"`` (plain
  JSON service calls such as ``getBaseInfo``).
- ``result``: the model used to parse the response ``data`` (``RawObject``
  when omitted).
- ``dc_type``: which DC pool receives the request.
- ``api_version``: overrides the envelope ``api_version`` when set.
- ``retries``: overrides the retry count (``0`` mirrors ``try_count: 0``).
- ``unwrap_auth_on_success``: the response carries a fresh ``auth`` to store.
"""

from __future__ import annotations

import enum
from abc import ABC
from dataclasses import dataclass, fields, is_dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Generic, Literal, Optional, TypeVar, cast

from rubigram.enums import DcType

if TYPE_CHECKING:  # pragma: no cover
    pass

ResultT = TypeVar("ResultT", covariant=True)

AuthMode = Literal["auth", "tmp", "none"]


def serialize_value(value: Any) -> Any:
    """Convert a Python value into its JSON-compatible RPC representation."""
    if isinstance(value, enum.Enum):
        return value.value
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: serialize_value(getattr(value, f.name)) for f in fields(value) if getattr(value, f.name) is not None}
    if isinstance(value, (list, tuple, set)):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialize_value(item) for key, item in value.items() if item is not None}
    return value


@dataclass
class RawMethod(ABC, Generic[ResultT]):
    """Declarative description of one RPC call (see the module docstring)."""

    method_name: ClassVar[str] = ""
    auth_mode: ClassVar[AuthMode] = "auth"
    unwrap_auth_on_success: ClassVar[bool] = False
    result: ClassVar[Any] = None
    dc_type: ClassVar[DcType] = DcType.API
    api_version: ClassVar[Optional[str]] = None
    retries: ClassVar[Optional[int]] = None
    omit_none: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if type(self) is RawMethod:
            raise TypeError("RawMethod cannot be instantiated directly")
        if not type(self).method_name:
            raise TypeError(f"{type(self).__name__} does not declare method_name")

    @property
    def name(self) -> str:
        return type(self).method_name

    def to_input(self) -> Dict[str, Any]:
        """Serialize the dataclass fields into the RPC ``input`` dict."""
        payload: Dict[str, Any] = {}
        for field in fields(self):
            if not field.init:
                continue
            value = getattr(self, field.name)
            if value is None and self.omit_none:
                continue
            key = field.metadata.get("name", field.name)
            payload[key] = serialize_value(value)
        return payload

    def parse_response(self, client: Any, data: Any) -> ResultT:
        """Build the typed result (``result`` model, else :class:`RawObject`)."""
        result_cls = type(self).result
        if result_cls is None:
            from rubigram.types import RawObject

            result_cls = RawObject
        if data is None:
            data = {}
        return cast(ResultT, result_cls._parse(client, data))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.to_input()!r})"


__all__ = ["AuthMode", "RawMethod", "ResultT", "serialize_value"]
