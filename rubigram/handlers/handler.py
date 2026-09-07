"""Handler base class and propagation-control exceptions."""

from __future__ import annotations

import inspect
from typing import Any, Callable, ClassVar, Optional


class StopPropagation(Exception):
    """Raise inside a handler to stop every remaining handler for this update."""


class ContinuePropagation(Exception):
    """Raise inside a handler to let the next handler of the same group run too."""


class Handler:
    """A callback with an optional filter, registered for one update kind."""

    kind: ClassVar[str] = "raw"

    def __init__(self, callback: Callable[..., Any], filters: Any = None):
        self.callback = callback
        self.filters = filters

    async def check(self, client: Any, update: Any) -> bool:
        if self.filters is None:
            return True
        result = self.filters(client, update)
        if inspect.isawaitable(result):
            result = await result
        return bool(result)

    async def invoke(self, client: Any, update: Any) -> Any:
        result = self.callback(client, update)
        if inspect.isawaitable(result):
            result = await result
        return result

    def __repr__(self) -> str:
        name = getattr(self.callback, "__name__", repr(self.callback))
        return f"{type(self).__name__}({name}, filters={self.filters!r})"


__all__ = ["Handler", "StopPropagation", "ContinuePropagation"]
