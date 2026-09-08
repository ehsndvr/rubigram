"""Base class of every typed model.

Models are ``@dataclass(kw_only=True)`` subclasses of :class:`Object`.  The
generic :meth:`Object._parse` maps a server dict onto the declared fields
using the type hints (nested models, lists of models, enums), keeps every
unknown key both as an attribute and in :attr:`Object.extra`, and binds the
client so bound methods (``message.reply()`` …) work.

Use the :func:`model` decorator instead of ``dataclass`` so the shared
``__repr__``/``__str__`` are kept::

    @model
    class User(Object):
        user_guid: str | None = None
        first_name: str | None = None
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import enum
import json
import types as _types
import typing
from dataclasses import InitVar, dataclass, fields, is_dataclass
from typing import Any, Callable, ClassVar, Optional, TypeVar, Union, get_args, get_origin, get_type_hints

if typing.TYPE_CHECKING:
    from typing_extensions import dataclass_transform
else:
    try:  # Python 3.11+
        from typing import dataclass_transform
    except ImportError:  # pragma: no cover - Python 3.10

        def dataclass_transform(**_kwargs: Any) -> Callable[[T], T]:
            def decorator(value: T) -> T:
                return value

            return decorator


if typing.TYPE_CHECKING:  # pragma: no cover - typing only
    import rubigram

T = TypeVar("T", bound="Object")

_MISSING = object()


def _parse_dynamic(client: Any, value: Any) -> Any:
    """Turn nested dicts/lists of an unknown field into :class:`RawObject` trees."""
    if isinstance(value, dict):
        from .raw_object import RawObject

        return RawObject._parse(client, value)
    if isinstance(value, list):
        return [_parse_dynamic(client, item) for item in value]
    return value


def _apply_unknown_fields(target: Object, client: Any, data: dict[str, Any], known_fields: typing.Iterable[str]) -> None:
    """Attach keys of ``data`` that are not in ``known_fields`` to ``target``."""
    known = set(known_fields)
    for key, value in data.items():
        if key not in known:
            parsed = _parse_dynamic(client, value)
            target.extra[key] = parsed
            if (
                not key.startswith("_")
                and key.isidentifier()
                and not isinstance(getattr(type(target), key, None), (property, classmethod, staticmethod))
                and not callable(getattr(type(target), key, None))
            ):
                setattr(target, key, parsed)


@dataclass(eq=False, repr=False)
class Object:
    """Base class for every typed model; see the module docstring."""

    client: InitVar[Any] = None

    _converters: ClassVar[Optional[dict[str, Callable[[Any, Any], Any]]]] = None
    _client: Any = dataclasses.field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self, client: Any = None) -> None:
        self._client = client

    # -- unknown fields -----------------------------------------------------

    @property
    def extra(self) -> dict[str, Any]:
        """Server keys that are not declared as fields (kept verbatim)."""
        store = self.__dict__.get("_extra")
        if store is None:
            store = {}
            self.__dict__["_extra"] = store
        return store

    # -- parsing --------------------------------------------------------------

    @classmethod
    def _field_converters(cls) -> dict[str, Callable[[Any, Any], Any]]:
        cached = cls.__dict__.get("_converters")
        if cached is not None:
            return cached
        converters: dict[str, Callable[[Any, Any], Any]] = {}
        hints = _resolve_type_hints(cls)
        for field in fields(cls):
            if not field.init or field.name.startswith("_"):
                continue
            converters[field.name] = _converter_for(hints.get(field.name, Any))
        cls._converters = converters
        return converters

    @classmethod
    def _parse(cls: type[T], client: Any, data: Any) -> Any:
        """Build an instance (or a list of instances) from server data."""
        if data is None:
            return None
        if isinstance(data, cls):
            data.bind(client)
            return data
        if isinstance(data, list):
            return [cls._parse(client, item) for item in data]
        if not isinstance(data, dict):
            return data
        converters = cls._field_converters()
        kwargs: dict[str, Any] = {}
        for name, convert in converters.items():
            if name in data:
                kwargs[name] = convert(client, data[name])
        instance = cls(client=client, **kwargs)
        _apply_unknown_fields(instance, client, data, converters.keys())
        instance.__post_parse__(client, data)
        return instance

    def __post_parse__(self, client: Any, data: dict[str, Any]) -> None:
        """Hook for models that derive fields from the raw payload."""

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any], client: Any = None) -> T:
        return cls._parse(client, data)

    # -- serialization ------------------------------------------------------

    def to_dict(self, *, include_none: bool = False) -> dict[str, Any]:
        """Plain dict of the declared fields plus :attr:`extra`."""
        result: dict[str, Any] = {}
        for field in fields(self):
            if not field.init or field.name.startswith("_"):
                continue
            value = getattr(self, field.name, None)
            if value is None and not include_none:
                continue
            result[field.name] = _to_plain(value, include_none)
        for key, value in self.extra.items():
            result[key] = _to_plain(value, include_none)
        return result

    def bind(self, client: rubigram.Client) -> None:
        """Bind a client to this object and every nested object."""
        self._client = client
        for value in self.__dict__.values():
            _bind_nested(value, client)

    # -- dunder -------------------------------------------------------------

    @staticmethod
    def default(obj: Any) -> Any:
        """``json.dumps`` default used by :meth:`__str__`."""
        if isinstance(obj, bytes):
            return repr(obj)
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, (_dt.datetime, _dt.date)):
            return str(obj)
        if isinstance(obj, Object):
            body = {"_": obj.__class__.__name__}
            for key, value in obj.to_dict().items():
                body[key] = "*" * 9 if key in {"phone", "phone_number"} else value
            return body
        return str(obj)

    def __str__(self) -> str:
        return json.dumps(self, indent=4, default=Object.default, ensure_ascii=False)

    def __repr__(self) -> str:
        parts = ", ".join(f"{key}={value!r}" for key, value in self.to_dict().items())
        return f"rubigram.types.{self.__class__.__name__}({parts})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Object) or type(self) is not type(other):
            return NotImplemented
        return self.to_dict(include_none=True) == other.to_dict(include_none=True)

    def __getstate__(self) -> dict[str, Any]:
        state = dict(self.__dict__)
        state.pop("_client", None)
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        self.__dict__.setdefault("_client", None)


@dataclass_transform(kw_only_default=True, eq_default=False)
def model(cls: type[T]) -> type[T]:
    """Decorator turning a class into a keyword-only rubigram model."""
    return dataclass(kw_only=True, eq=False, repr=False)(cls)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve_type_hints(cls: type) -> dict[str, Any]:
    """Resolve annotations using the module globals plus the whole ``rubigram.types`` namespace.

    Models reference each other across modules (``UserInfo.chat`` is a
    ``Chat`` defined in ``chat.py``); evaluating the string annotations against
    the package namespace avoids circular imports.
    """
    import sys

    namespace: dict[str, Any] = {"InitVar": InitVar, "ClassVar": ClassVar, "Any": Any, "Optional": Optional, "Callable": Callable}
    package = sys.modules.get("rubigram.types")
    if package is not None:
        namespace.update(vars(package))
    # Base classes first so that the most derived module wins on name clashes.
    for klass in reversed(cls.__mro__):
        module = sys.modules.get(getattr(klass, "__module__", ""))
        if module is not None:
            namespace.update(vars(module))
    try:
        return get_type_hints(cls, globalns=namespace)
    except Exception:  # pragma: no cover - unresolved forward references fall back to raw values
        return {}


def _is_optional(hint: Any) -> tuple[bool, Any]:
    origin = get_origin(hint)
    if origin is Union or origin is _types.UnionType:
        args = [arg for arg in get_args(hint) if arg is not type(None)]
        if len(args) == 1:
            return True, args[0]
        return True, Any
    return False, hint


def _converter_for(hint: Any) -> Callable[[Any, Any], Any]:
    _, inner = _is_optional(hint)
    origin = get_origin(inner)
    if origin in (list, typing.List):
        (item_hint,) = get_args(inner) or (Any,)
        item = _converter_for(item_hint)

        def convert_list(client: Any, value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, list):
                return [item(client, element) for element in value]
            return item(client, value)

        return convert_list
    if origin in (dict, typing.Dict):
        return lambda client, value: value
    if isinstance(inner, type):
        if issubclass(inner, Object):
            return lambda client, value: inner._parse(client, value)
        if issubclass(inner, enum.Enum):

            def convert_enum(client: Any, value: Any) -> Any:
                if value is None or isinstance(value, inner):
                    return value
                try:
                    return inner(value)
                except ValueError:
                    return value

            return convert_enum
    return lambda client, value: value


def _to_plain(value: Any, include_none: bool) -> Any:
    if isinstance(value, Object):
        return value.to_dict(include_none=include_none)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, list):
        return [_to_plain(item, include_none) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item, include_none) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return value


def _bind_nested(value: Any, client: Any) -> None:
    if isinstance(value, Object):
        value.bind(client)
    elif isinstance(value, list):
        for item in value:
            _bind_nested(item, client)
    elif isinstance(value, dict):
        for item in value.values():
            _bind_nested(item, client)


__all__ = ["Object", "_apply_unknown_fields", "_parse_dynamic", "model"]
