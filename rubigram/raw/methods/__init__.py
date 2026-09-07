"""Every raw RPC method, plus a registry keyed by the Rubika method name."""

from __future__ import annotations

from typing import Dict, Type

from rubigram.raw.base import RawMethod
from rubigram.raw.methods import auth, channels, chats, files, groups, messages, services, settings, stickers, users
from rubigram.raw.methods.auth import *  # noqa: F403
from rubigram.raw.methods.channels import *  # noqa: F403
from rubigram.raw.methods.chats import *  # noqa: F403
from rubigram.raw.methods.files import *  # noqa: F403
from rubigram.raw.methods.groups import *  # noqa: F403
from rubigram.raw.methods.messages import *  # noqa: F403
from rubigram.raw.methods.services import *  # noqa: F403
from rubigram.raw.methods.settings import *  # noqa: F403
from rubigram.raw.methods.stickers import *  # noqa: F403
from rubigram.raw.methods.users import *  # noqa: F403

_MODULES = (auth, users, chats, messages, groups, channels, files, stickers, settings, services)

__all__ = [name for module in _MODULES for name in module.__all__] + ["METHODS", "method_for"]  # pyright: ignore[reportUnsupportedDunderAll]


def _build_registry() -> Dict[str, Type[RawMethod]]:
    registry: Dict[str, Type[RawMethod]] = {}
    for module in _MODULES:
        for name in module.__all__:
            cls = getattr(module, name)
            if isinstance(cls, type) and issubclass(cls, RawMethod) and cls.method_name:
                # The first (canonical) class wins; deprecated aliases come after it.
                registry.setdefault(cls.method_name, cls)
    return registry


METHODS: Dict[str, Type[RawMethod]] = _build_registry()


def method_for(method_name: str) -> Type[RawMethod]:
    """Return the raw class for a Rubika method name (``KeyError`` when unknown)."""
    return METHODS[method_name]
