"""Rotating URL pool per DC type (mirrors ``activeIndexDcs`` / ``nextUrlLocked`` of the web client)."""

from __future__ import annotations

import time
from typing import Iterable, List, Optional

from rubigram.errors import TransportError


class UrlPool:
    """A list of equivalent URLs with a current index and rotation lock.

    The web client rotates to the next DC URL before a retry but ignores
    further rotation requests for two seconds (``switchUrlDelay``) so that a
    burst of concurrent failures does not skip healthy DCs.  :meth:`rotate`
    implements that lock; :meth:`force_rotate` bypasses it.
    """

    def __init__(self, urls: Iterable[str] = (), *, switch_lock: float = 2.0):
        self._urls: List[str] = []
        self._current_index = 0
        self._switch_lock = switch_lock
        self._last_rotation: Optional[float] = None
        self.replace(urls, strict=False)

    @property
    def urls(self) -> List[str]:
        return list(self._urls)

    @property
    def count(self) -> int:
        return len(self._urls)

    @property
    def current(self) -> str:
        return self.get_current()

    def get_current(self) -> str:
        if not self._urls:
            raise TransportError("No URLs available in the pool")
        return self._urls[self._current_index]

    def has_url(self, url: str) -> bool:
        return url in self._urls

    def set_current(self, url: str) -> bool:
        """Make ``url`` current when it belongs to the pool; return whether it did."""
        if url in self._urls:
            self._current_index = self._urls.index(url)
            return True
        return False

    def rotate(self) -> str:
        """Advance to the next URL unless a rotation happened within the lock window."""
        now = time.monotonic()
        if self._last_rotation is not None and now - self._last_rotation < self._switch_lock:
            return self.get_current()
        return self.force_rotate()

    def force_rotate(self) -> str:
        if not self._urls:
            raise TransportError("No URLs available in the pool")
        self._current_index = (self._current_index + 1) % len(self._urls)
        self._last_rotation = time.monotonic()
        return self._urls[self._current_index]

    def reset(self) -> None:
        self._current_index = 0
        self._last_rotation = None

    def replace(self, urls: Iterable[str], *, strict: bool = True) -> None:
        """Replace the URL list, keeping the current URL when it survives."""
        deduped: List[str] = []
        for url in urls:
            if url and url not in deduped:
                deduped.append(str(url))
        if not deduped:
            if strict:
                raise TransportError("No URLs available in the pool")
            self._urls = []
            self._current_index = 0
            return
        current = self._urls[self._current_index] if self._urls else None
        self._urls = deduped
        self._current_index = deduped.index(current) if current in deduped else 0

    def __len__(self) -> int:
        return len(self._urls)

    def __iter__(self):
        return iter(self._urls)

    def __repr__(self) -> str:
        return f"UrlPool({self._urls!r}, current={self._current_index})"


# Backward-compatible name used by the previous transport module.
ApiUrlPool = UrlPool

__all__ = ["ApiUrlPool", "UrlPool"]
