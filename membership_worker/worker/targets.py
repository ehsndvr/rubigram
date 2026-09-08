"""Parsing of the ``target`` a panel order refers to.

Rubika targets come in five shapes::

    https://rubika.ir/joinc/<32 hex>     private channel invite   → kind "channel_link"
    https://rubika.ir/joing/<32 hex>     group invite             → kind "group_link"
    @name / https://rubika.ir/name       public channel username  → kind "username"
    c0… / g0… guid                       channel / group guid     → kind "guid"
    https://rubika.ir/name/<message id>  one channel post         → kind "post"

``normalize_target_key`` turns any of them into the key used for de-duplicating
memberships, so ``@Name``, ``rubika.ir/name`` and ``https://rubika.ir/name/``
map to the same account/target pair.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

_HOSTS = {"rubika.ir", "www.rubika.ir", "m.rubika.ir", "web.rubika.ir"}
_HASH_RE = re.compile(r"^[A-Za-z0-9]{16,64}$")
_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,63}$")
_GUID_RE = re.compile(r"^[ugcbs]0[A-Za-z0-9]{30}$")


class TargetError(ValueError):
    """The target string cannot be understood."""


@dataclass(frozen=True)
class TargetRef:
    kind: str  # channel_link | group_link | username | guid | post
    value: str  # hash, username, guid …
    message_id: str = ""  # only for kind == "post"

    @property
    def key(self) -> str:
        if self.kind == "channel_link":
            return f"joinc:{self.value}"
        if self.kind == "group_link":
            return f"joing:{self.value}"
        if self.kind == "post":
            return f"post:{self.value.lower()}:{self.message_id}"
        if self.kind == "guid":
            return f"guid:{self.value}"
        return f"user:{self.value.lower()}"

    @property
    def is_group(self) -> bool:
        return self.kind == "group_link" or (self.kind == "guid" and self.value.startswith("g0"))


def parse_target(raw_value: str) -> TargetRef:
    """Classify a target string; raises :class:`TargetError` when it is not usable."""
    value = (raw_value or "").strip()
    if not value:
        raise TargetError("target is empty")
    if _GUID_RE.match(value):
        if value[0] not in "cg":
            raise TargetError("only channel (c0…) and group (g0…) guids can be targets")
        return TargetRef("guid", value)
    if value.startswith("@"):
        return _username(value[1:])
    if "://" not in value and "/" not in value:
        return _username(value)
    url = value if "://" in value else f"https://{value}"
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host not in _HOSTS:
        raise TargetError(f"unsupported host {host or value!r}; expected a rubika.ir link")
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        raise TargetError("link has no path")
    head = parts[0].lower()
    if head in {"joinc", "joing"}:
        if len(parts) < 2 or not _HASH_RE.match(parts[1]):
            raise TargetError("invite link has no hash")
        return TargetRef("channel_link" if head == "joinc" else "group_link", parts[1])
    if len(parts) >= 2 and parts[1].isdigit():
        return TargetRef("post", _username(parts[0]).value, message_id=parts[1])
    return _username(parts[0])


def _username(value: str) -> TargetRef:
    name = value.strip().lstrip("@")
    if not _USERNAME_RE.match(name):
        raise TargetError(f"{value!r} is not a valid Rubika username")
    return TargetRef("username", name)


def normalize_target_key(raw_value: str) -> str:
    """Stable key of a target (see the module docstring)."""
    return parse_target(raw_value).key


__all__ = ["TargetError", "TargetRef", "normalize_target_key", "parse_target"]
