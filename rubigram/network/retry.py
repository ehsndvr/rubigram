"""Retry policy shared by every transport.

The default ladder is the one used by web.rubika.ir 4.4.34: up to five
retries with delays ``0, 2, 3, 5, 10`` seconds, switching to the next DC URL
before each retry, and a 20 second request timeout.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from typing import Awaitable, Callable, Optional, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")

WEB_RETRY_DELAYS: tuple[float, ...] = (0.0, 2.0, 3.0, 5.0, 10.0)


@dataclass(frozen=True)
class RetryPolicy:
    """How many times a request is retried, how long to wait, and the timeout.

    Attributes:
        delays: seconds to sleep before retry ``n`` (``delays[n]``); the number
            of retries is ``len(delays)`` unless ``max_retries`` caps it.
        timeout: per-attempt timeout in seconds.
        max_retries: optional cap on the number of retries (``0`` disables
            retries, like ``try_count: 0`` in the web client).
    """

    delays: tuple[float, ...] = WEB_RETRY_DELAYS
    timeout: float = 20.0
    max_retries: Optional[int] = None

    @property
    def retries(self) -> int:
        if self.max_retries is None:
            return len(self.delays)
        return max(0, min(self.max_retries, len(self.delays)) if self.delays else self.max_retries)

    @property
    def attempts(self) -> int:
        return self.retries + 1

    def delay_for(self, retry_index: int) -> float:
        """Delay before the ``retry_index``-th retry (0-based)."""
        if not self.delays:
            return 0.0
        return float(self.delays[min(retry_index, len(self.delays) - 1)])

    def with_overrides(self, *, retries: Optional[int] = None, timeout: Optional[float] = None) -> "RetryPolicy":
        """Return a copy with a different retry count and/or timeout."""
        policy = self
        if retries is not None:
            policy = replace(policy, max_retries=max(0, int(retries)))
        if timeout is not None:
            policy = replace(policy, timeout=float(timeout))
        return policy


DEFAULT_RETRY_POLICY = RetryPolicy()
NO_RETRY = RetryPolicy(delays=(), timeout=20.0, max_retries=0)


async def run_with_retries(
    policy: RetryPolicy,
    attempt: Callable[[int], Awaitable[T]],
    *,
    retryable: Callable[[BaseException], bool],
    on_retry: Optional[Callable[[int, BaseException], Awaitable[None] | None]] = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    label: str = "request",
) -> T:
    """Run ``attempt(index)`` until it succeeds or the policy is exhausted.

    ``retryable(exc)`` decides whether a failure may be retried; ``on_retry``
    runs before each retry (for example to rotate the DC URL).  The last
    exception is re-raised unchanged when no attempt is left.
    """
    last_error: Optional[BaseException] = None
    for index in range(policy.attempts):
        try:
            return await attempt(index)
        except asyncio.CancelledError:
            raise
        except BaseException as exc:  # noqa: BLE001 - the predicate decides
            last_error = exc
            if index >= policy.retries or not retryable(exc):
                raise
            delay = policy.delay_for(index)
            log.debug("%s failed (%s); retry %d/%d in %.1fs", label, exc, index + 1, policy.retries, delay)
            if on_retry is not None:
                result = on_retry(index, exc)
                if result is not None:
                    await result
            if delay > 0:
                await sleep(delay)
    assert last_error is not None  # pragma: no cover - loop always sets it before falling through
    raise last_error


__all__ = ["RetryPolicy", "DEFAULT_RETRY_POLICY", "NO_RETRY", "WEB_RETRY_DELAYS", "run_with_retries"]
