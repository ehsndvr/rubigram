"""A single event loop in a background thread for the request handlers.

Django views are synchronous under Daphne's thread pool; the login flow needs
``await``.  Running one persistent loop (instead of ``asyncio.run()`` per
request) keeps every rubigram client on the loop it was created on.
"""

from __future__ import annotations

import asyncio
import atexit
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

DEFAULT_TIMEOUT = 120.0


class AsyncRuntime:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def run(self, coro: Coroutine[Any, Any, T], timeout: float = DEFAULT_TIMEOUT) -> T:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise TimeoutError(f"async operation did not complete within {timeout:g}s") from None

    def shutdown(self) -> None:
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(loop.stop)

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is not None and self._loop.is_running():
                return self._loop
            ready = threading.Event()

            def runner() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                ready.set()
                loop.run_forever()
                loop.close()

            self._thread = threading.Thread(target=runner, name="membership-worker-async", daemon=True)
            self._thread.start()
            ready.wait(timeout=5)
            if self._loop is None or not self._loop.is_running():
                raise RuntimeError("async runtime did not start")
            return self._loop


runtime = AsyncRuntime()
atexit.register(runtime.shutdown)


def run_async(coro: Coroutine[Any, Any, T], timeout: float = DEFAULT_TIMEOUT) -> T:
    return runtime.run(coro, timeout=timeout)


__all__ = ["AsyncRuntime", "run_async", "runtime"]
