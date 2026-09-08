"""Is this session still alive — and is it still useful?

Two questions the job pipeline cannot answer.  It only ever learns about an
account by *using* it, so a number registered ten minutes ago has no verdict at
all, and an account disabled by a dropped connection looks exactly like one
whose session Rubika has thrown away.  Both are the moment somebody most wants
to know, and both used to answer "nothing recorded".

So this connects on purpose, reads one thing, and writes down what happened:

* ``alive``     — ``getUserInfo`` answered for this session.
* ``auth_fail`` — Rubika refused the session (``InvalidAuth`` and friends).
* ``transient`` — the network, a timeout, a rate limit.  Says nothing about the
  account, and is never allowed to condemn one.

Strictly read-only.  It never joins, leaves, views or reacts; the account is
untouched apart from having been connected to.

Two rules keep the verdicts honest.  ``auth_fail`` must happen twice running
before an account is called dead — one refusal is as likely to be the route as
the session — and an ``alive`` probe *reactivates* an account the job pipeline
had disabled, because a session that authenticates now is one the pipeline was
wrong about.

What this cannot do is detect a full account.  Rubika, like Bale, has a ceiling
on how many channels one account may join and no read-only way to ask about it:
a capacity-limited account reads, resolves and identifies itself perfectly, and
only a *join* comes back refused.  So ``at_capacity`` is recognised from the
refusal the job pipeline already recorded, never from the probe.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

from django.conf import settings
from django.db import close_old_connections
from django.db.models import Count
from django.utils import timezone

from .models import WorkerAccount, WorkerAccountHealth
from .rubika import ActionError, build_client, classify_error

log = logging.getLogger("membership_worker.health")

ALIVE = WorkerAccountHealth.ALIVE
AUTH_FAIL = WorkerAccountHealth.AUTH_FAIL
TRANSIENT = WorkerAccountHealth.TRANSIENT

Availability = WorkerAccountHealth.Availability

#: Consecutive refusals before an account is called dead.  Hysteresis, so one
#: fluke never costs a working session.
DEAD_THRESHOLD = 2

#: A recorded ``last_error`` naming any of these is a join that Rubika refused
#: for capacity.  The wording differs between Rubika's own message and the
#: worker's Persian rendering of it, so both are matched.
_CAPACITY_KEYWORDS = ("join_limit", "max_group", "maximum", "capacity", "ظرفیت")

#: How many probes run at once.  Each holds a connection open for its whole
#: timeout, so this bounds the request, not the database.
DEFAULT_CONCURRENCY = 8


def is_capacity_error(last_error: str) -> bool:
    """Does this recorded error mean the account is full rather than broken?"""
    text = (last_error or "").lower()
    return any(word in text for word in _CAPACITY_KEYWORDS)


@dataclass(frozen=True)
class _Target:
    """Everything a probe needs, frozen before it starts.

    Copied out of the ORM on purpose: the probes run together on an event loop,
    and a model instance carried in there is a database connection used from a
    place Django does not expect it to be used from.
    """

    account_id: int
    session_name: str
    phone: str
    session_string: str
    status: str
    last_error: str


@dataclass(frozen=True)
class ProbeResult:
    account_id: int
    session_name: str
    phone: str
    outcome: str
    detail: str
    availability: str

    @property
    def alive(self) -> bool:
        return self.outcome == ALIVE


# ── the probe itself ──────────────────────────────────────────────────────────


async def _probe_one(target: _Target, *, timeout: float) -> tuple[str, str]:
    """Connect as this account and read one thing.  Returns ``(outcome, detail)``."""
    if not target.session_string:
        return AUTH_FAIL, "account has no stored session"
    client = build_client(target.session_name, target.session_string, timeout=timeout)
    try:
        await client.start()
        me = await client.get_me()
    except Exception as exc:
        action = classify_error(exc)
        outcome = AUTH_FAIL if action.kind == ActionError.SESSION_DEAD else TRANSIENT
        return outcome, str(action)[:2000]
    finally:
        try:
            await client.stop()
        except Exception:
            log.debug("closing probe client %s failed", target.session_name[:16], exc_info=True)

    user = getattr(me, "user", None)
    guid = getattr(user, "user_guid", None) if user is not None else None
    # An answer with no user in it is not an authenticated read; treat it as a
    # transient oddity rather than proof of either verdict.
    if not guid:
        return TRANSIENT, "getUserInfo answered without a user"
    return ALIVE, ""


async def _probe_all(targets: list[_Target], *, timeout: float, concurrency: int) -> dict[int, tuple[str, str]]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def one(target: _Target) -> tuple[int, tuple[str, str]]:
        async with semaphore:
            try:
                return target.account_id, await _probe_one(target, timeout=timeout)
            except Exception as exc:  # pragma: no cover - _probe_one catches its own
                return target.account_id, (TRANSIENT, str(exc)[:2000])

    return dict(await asyncio.gather(*(one(t) for t in targets)))


# ── classification and persistence ────────────────────────────────────────────


def _availability_for(target: _Target, outcome: str, failures: int) -> str:
    if outcome == ALIVE:
        return Availability.AT_CAPACITY if is_capacity_error(target.last_error) else Availability.AVAILABLE
    if outcome == AUTH_FAIL:
        return Availability.DEAD if failures >= DEAD_THRESHOLD else Availability.UNKNOWN
    # Transient: whatever we knew before is still the best answer we have, and
    # "we could not reach it" is not news about the account.
    return ""


def _record(target: _Target, outcome: str, detail: str) -> ProbeResult:
    """Persist one verdict and return it, reactivating a wrongly disabled account."""
    close_old_connections()
    health, _ = WorkerAccountHealth.objects.get_or_create(account_id=target.account_id)
    failures = health.consecutive_auth_failures + 1 if outcome == AUTH_FAIL else 0
    availability = _availability_for(target, outcome, failures) or health.availability or Availability.UNKNOWN

    health.outcome = outcome
    health.detail = detail[:2000]
    health.consecutive_auth_failures = failures
    health.availability = availability
    health.last_checked_at = timezone.now()
    health.save()

    # A session that authenticates now is one the job pipeline was wrong about:
    # most disabled accounts were disabled by a glitch, not by Rubika.
    if outcome == ALIVE and target.status != WorkerAccount.Status.ACTIVE:
        WorkerAccount.objects.filter(id=target.account_id).update(
            status=WorkerAccount.Status.ACTIVE, last_error="", updated_at=timezone.now()
        )
        log.info("probe reactivated account=%s session=%s", target.account_id, target.session_name[:16])
    elif outcome == AUTH_FAIL and availability == Availability.DEAD and target.status == WorkerAccount.Status.ACTIVE:
        WorkerAccount.objects.filter(id=target.account_id).update(
            status=WorkerAccount.Status.DISABLED, last_error=detail[:2000], updated_at=timezone.now()
        )
        log.info("probe disabled account=%s session=%s", target.account_id, target.session_name[:16])

    return ProbeResult(
        account_id=target.account_id,
        session_name=target.session_name,
        phone=target.phone,
        outcome=outcome,
        detail=detail,
        availability=availability,
    )


def _targets_for(*, session_names: Optional[list[str]] = None, limit: Optional[int] = None) -> list[_Target]:
    close_old_connections()
    rows = WorkerAccount.objects.select_related("credential")
    if session_names is not None:
        rows = rows.filter(session_name__in=session_names)
    else:
        # Whatever has been waiting longest, so a scan that cannot finish the
        # table still works its way round it. Nulls (never probed) sort first on
        # every backend this runs on when ordered by the related field's id.
        rows = rows.order_by("health__last_checked_at", "id")
    if limit:
        rows = rows[:limit]
    return [
        _Target(
            account_id=row.id,
            session_name=row.session_name,
            phone=row.phone,
            session_string=getattr(getattr(row, "credential", None), "session_string", "") or "",
            status=row.status,
            last_error=row.last_error,
        )
        for row in rows
    ]


# ── the two entry points ──────────────────────────────────────────────────────


def probe_sessions(
    session_names: list[str],
    *,
    timeout: Optional[float] = None,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> tuple[dict[str, ProbeResult], list[str]]:
    """Probe these sessions now.  Returns ``(verdicts by session name, missing)``."""
    targets = _targets_for(session_names=session_names)
    found = {t.session_name for t in targets}
    missing = [name for name in session_names if name not in found]
    if not targets:
        return {}, missing

    seconds = float(timeout or settings.WORKER_LOGIN_TIMEOUT_SECONDS)
    outcomes = asyncio.run(_probe_all(targets, timeout=seconds, concurrency=concurrency))
    results: dict[str, ProbeResult] = {}
    for target in targets:
        outcome, detail = outcomes.get(target.account_id, (TRANSIENT, "probe did not run"))
        results[target.session_name] = _record(target, outcome, detail)
    return results, missing


def scan_accounts(limit: int = 100) -> int:
    """The periodic sweep: probe the accounts nobody has looked at for longest."""
    targets = _targets_for(limit=limit)
    if not targets:
        return 0
    seconds = float(settings.WORKER_LOGIN_TIMEOUT_SECONDS)
    outcomes = asyncio.run(_probe_all(targets, timeout=seconds, concurrency=DEFAULT_CONCURRENCY))
    for target in targets:
        outcome, detail = outcomes.get(target.account_id, (TRANSIENT, "probe did not run"))
        _record(target, outcome, detail)
    log.info("health scan probed %d accounts", len(targets))
    return len(targets)


def availability_snapshot() -> dict[str, Any]:
    """The rollup the panel's health dashboard shows.  Four counts and a timestamp."""
    close_old_connections()
    buckets = dict.fromkeys(Availability.values, 0)
    for row in WorkerAccountHealth.objects.values("availability").annotate(n=Count("id")):
        if row["availability"] in buckets:
            buckets[row["availability"]] = row["n"]
    total = WorkerAccount.objects.count()
    # Accounts with no health row at all have not been probed, and saying so is
    # the point of the bucket — otherwise a worker that never ran a scan reports
    # a tidy set of zeroes that reads like "nothing is wrong".
    buckets[Availability.UNKNOWN] = total - sum(v for k, v in buckets.items() if k != Availability.UNKNOWN)
    last = WorkerAccountHealth.objects.order_by("-last_checked_at").values_list("last_checked_at", flat=True).first()
    return {
        "total": total,
        "available": buckets[Availability.AVAILABLE],
        "at_capacity": buckets[Availability.AT_CAPACITY],
        "dead": buckets[Availability.DEAD],
        "unknown": max(0, buckets[Availability.UNKNOWN]),
        "last_scan_at": last.isoformat() if last else None,
    }


def availability_map(session_names: list[str]) -> dict[str, dict[str, Any]]:
    """What the last probe recorded for each of these sessions."""
    close_old_connections()
    rows = WorkerAccountHealth.objects.filter(account__session_name__in=session_names).values(
        "account__session_name", "availability", "outcome", "detail", "last_checked_at"
    )
    return {
        row["account__session_name"]: {
            "availability": row["availability"],
            "outcome": row["outcome"],
            "detail": row["detail"],
            "last_checked_at": row["last_checked_at"].isoformat() if row["last_checked_at"] else None,
        }
        for row in rows
    }


__all__ = [
    "ALIVE",
    "AUTH_FAIL",
    "DEAD_THRESHOLD",
    "TRANSIENT",
    "Availability",
    "ProbeResult",
    "availability_map",
    "availability_snapshot",
    "is_capacity_error",
    "probe_sessions",
    "scan_accounts",
]
