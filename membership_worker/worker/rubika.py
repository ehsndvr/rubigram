"""Everything that touches Rubika through rubigram: clients, join, leave, view, member counts.

Each action opens a short-lived client from the account's session string
(HTTP only, no socket, no DC re-discovery), performs one operation and closes.
Failures are classified into :class:`ActionError` kinds so the item processor
can decide between "retry with another account", "the target is wrong" and
"this account is dead".
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from django.conf import settings

from rubigram import Client, errors
from rubigram.network import RetryPolicy
from rubigram.utils import device_hash_from_user_agent

from .targets import TargetError, TargetRef, parse_target

log = logging.getLogger("membership_worker.rubika")
T = TypeVar("T")


class ActionError(RuntimeError):
    """A Rubika action failed; ``kind`` tells the item processor what to do."""

    INVALID_TARGET = "invalid_target"  # no account can succeed on this target
    SESSION_DEAD = "session_dead"  # the account must be disabled
    THROTTLED = "throttled"  # TOO_REQUESTS: pause the account
    CONN_ERROR = "conn_error"  # network problem: the account is fine
    ALREADY_DONE = "already_done"  # already a member (join) / not a member (leave)
    FAILED = "failed"  # anything else

    def __init__(self, kind: str, message: str, *, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after


@dataclass(frozen=True)
class ResolvedTarget:
    object_guid: str
    object_type: str  # "Channel" | "Group"
    title: str
    member_count: Optional[int]
    is_member: Optional[bool]
    ref: TargetRef


@dataclass(frozen=True)
class JoinOutcome:
    object_guid: str
    object_type: str
    title: str
    member_count_before: Optional[int]
    member_count_after: Optional[int]
    session_string: Optional[str] = None  # refreshed session, when it changed


@dataclass(frozen=True)
class LeaveOutcome:
    object_guid: str
    object_type: str
    title: str
    session_string: Optional[str] = None


@dataclass(frozen=True)
class ViewOutcome:
    object_guid: str
    message_ids: list[str]
    session_string: Optional[str] = None


# ── clients ───────────────────────────────────────────────────────────────────


def worker_user_agent() -> str:
    from rubigram.network.headers import CHROME_USER_AGENT

    return str(settings.WORKER_USER_AGENT or CHROME_USER_AGENT)


def worker_device_hash() -> str:
    return str(settings.WORKER_DEVICE_HASH or device_hash_from_user_agent(worker_user_agent()))


def client_kwargs(*, timeout: Optional[float] = None) -> dict[str, Any]:
    per_request = float(timeout or settings.WORKER_ACTION_TIMEOUT_SECONDS)
    return {
        "in_memory": True,
        "interactive": False,
        "enable_socket": False,
        "transport": "http",
        "timeout": per_request,
        "retry_policy": RetryPolicy(delays=(0, 2), timeout=per_request),
        "user_agent": worker_user_agent(),
        "device_hash": worker_device_hash(),
        "system_version": str(settings.WORKER_SYSTEM_VERSION),
        "device_model": str(settings.WORKER_DEVICE_MODEL),
        "proxy": str(settings.WORKER_PROXY) or None,
    }


def build_client(session_name: str, session_string: Optional[str] = None, *, timeout: Optional[float] = None) -> Client:
    """A throw-away client; with a session string it skips DC discovery and the base-info refresh."""
    kwargs = client_kwargs(timeout=timeout)
    if session_string:
        return Client.from_session_string(session_name, session_string, discover_dcs=False, refresh_base_info=False, **kwargs)
    return Client(session_name, **kwargs)


# ── error classification ───────────────────────────────────────────────────────


def classify_error(exc: BaseException) -> ActionError:
    if isinstance(exc, ActionError):
        return exc
    if isinstance(exc, TargetError):
        return ActionError(ActionError.INVALID_TARGET, str(exc))
    if isinstance(exc, errors.InvalidAuth | errors.NotRegistered | errors.LoginRequired | errors.SessionExpired):
        return ActionError(ActionError.SESSION_DEAD, f"session rejected: {exc}")
    if isinstance(exc, errors.TooRequests):
        return ActionError(ActionError.THROTTLED, f"too many requests: {exc}", retry_after=exc.retry_after)
    if isinstance(exc, errors.NetworkError | errors.TransportError | errors.DecodeError | asyncio.TimeoutError | TimeoutError | OSError):
        return ActionError(ActionError.CONN_ERROR, f"connection error: {exc}")
    return ActionError(ActionError.FAILED, str(exc) or type(exc).__name__)


# ── resolution ─────────────────────────────────────────────────────────────────


def _count(obj: Any) -> Optional[int]:
    value = getattr(obj, "count_members", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def resolve_target(client: Client, ref: TargetRef) -> ResolvedTarget:
    """Find the guid, title and member count behind a target without changing anything."""
    try:
        if ref.kind == "channel_link":
            preview = await client.get_channel_preview(ref.value)
            channel = preview.channel
            if preview.is_valid is False or channel is None or not channel.channel_guid:
                raise ActionError(ActionError.INVALID_TARGET, "channel invite link is invalid or expired")
            return ResolvedTarget(channel.channel_guid, "Channel", channel.channel_title or "", _count(channel), preview.is_member, ref)
        if ref.kind == "group_link":
            preview = await client.get_group_preview(ref.value)
            group = getattr(preview, "group", None)
            if getattr(preview, "is_valid", None) is False or group is None or not getattr(group, "group_guid", None):
                raise ActionError(ActionError.INVALID_TARGET, "group invite link is invalid or expired")
            return ResolvedTarget(
                group.group_guid, "Group", getattr(group, "group_title", "") or "", _count(group), getattr(preview, "is_member", None), ref
            )
        if ref.kind == "guid":
            if ref.value.startswith("c0"):
                info = await client.get_channel_info(ref.value)
                channel = info.channel
                if channel is None:
                    raise ActionError(ActionError.INVALID_TARGET, "channel not found")
                return ResolvedTarget(ref.value, "Channel", channel.channel_title or "", _count(channel), None, ref)
            group_info = await client.get_group_info(ref.value)
            group = group_info.group
            if group is None:
                raise ActionError(ActionError.INVALID_TARGET, "group not found")
            return ResolvedTarget(ref.value, "Group", getattr(group, "group_title", "") or "", _count(group), None, ref)
        # username or post
        found = await client.get_object_by_username(ref.value)
        if found.exist is False or not found.type:
            raise ActionError(ActionError.INVALID_TARGET, f"@{ref.value} does not exist")
        if found.type == "Channel" and found.channel is not None:
            channel = found.channel
            guid = getattr(channel, "channel_guid", None)
            if not guid:
                raise ActionError(ActionError.INVALID_TARGET, f"@{ref.value} has no channel guid")
            return ResolvedTarget(str(guid), "Channel", getattr(channel, "channel_title", "") or "", _count(channel), None, ref)
        if found.type == "Group" and found.group is not None:
            group = found.group
            guid = getattr(group, "group_guid", None)
            if not guid:
                raise ActionError(ActionError.INVALID_TARGET, f"@{ref.value} has no group guid")
            return ResolvedTarget(str(guid), "Group", getattr(group, "group_title", "") or "", _count(group), None, ref)
        raise ActionError(ActionError.INVALID_TARGET, f"@{ref.value} is a {found.type}, not a channel or group")
    except errors.InvalidInput as exc:
        raise ActionError(ActionError.INVALID_TARGET, f"target rejected by Rubika: {exc}") from exc


async def _member_count(client: Client, object_guid: str, object_type: str) -> Optional[int]:
    try:
        if object_type == "Channel":
            return _count((await client.get_channel_info(object_guid)).channel)
        return _count((await client.get_group_info(object_guid)).group)
    except errors.RubigramError:
        return None


# ── actions ─────────────────────────────────────────────────────────────────────


async def join_target(client: Client, ref: TargetRef, *, probe_after: bool) -> JoinOutcome:
    resolved = await resolve_target(client, ref)
    if resolved.is_member:
        raise ActionError(ActionError.ALREADY_DONE, "account is already a member")
    if ref.kind == "channel_link":
        joined: Any = await client.join_channel_by_link(ref.value)
        obj = joined.channel
    elif ref.kind == "group_link":
        joined = await client.join_group(ref.value)
        obj = joined.group
    elif resolved.object_type == "Channel":
        joined = await client.join_channel(resolved.object_guid)
        obj = joined.channel
    else:
        raise ActionError(ActionError.INVALID_TARGET, "groups can only be joined through an invite link")
    after = _count(obj)
    if after is None and probe_after:
        after = await _member_count(client, resolved.object_guid, resolved.object_type)
    title = (
        (getattr(obj, "channel_title", None) or getattr(obj, "group_title", None) or resolved.title or ref.value)
        if obj is not None
        else resolved.title
    )
    return JoinOutcome(resolved.object_guid, resolved.object_type, title, resolved.member_count, after)


async def leave_target(client: Client, ref: TargetRef) -> LeaveOutcome:
    resolved = await resolve_target(client, ref)
    if resolved.is_member is False:
        raise ActionError(ActionError.ALREADY_DONE, "account is not a member")
    if resolved.object_type == "Channel":
        await client.leave_channel(resolved.object_guid)
    else:
        await client.leave_group(resolved.object_guid)
    return LeaveOutcome(resolved.object_guid, resolved.object_type, resolved.title or ref.value)


async def view_posts(client: Client, ref: TargetRef, *, service_id: str) -> ViewOutcome:
    """Read the latest posts (or one post) of a channel and mark them seen, which counts a view."""
    resolved = await resolve_target(client, ref)
    guid = resolved.object_guid
    if ref.kind == "post":
        message = await client.get_message(guid, ref.message_id)
        if message is None:
            raise ActionError(ActionError.INVALID_TARGET, f"post {ref.message_id} was not found in @{ref.value}")
        ids = [str(message.message_id)]
    else:
        limit = int(settings.WORKER_VIEW_POST_COUNTS.get(str(service_id), 5))
        page = await client.get_messages(guid, limit=limit)
        ids = [str(m.message_id) for m in page.messages if m.message_id]
    if not ids:
        raise ActionError(ActionError.FAILED, "the channel has no posts to view")
    await client.seen_chats({guid: max(ids, key=int)})
    return ViewOutcome(guid, ids)


# ── sync runners (used by the Celery tasks) ──────────────────────────────────────


async def _with_client(session_name: str, session_string: str, fn: Callable[[Client], Awaitable[T]]) -> tuple[T, Optional[str]]:
    client = build_client(session_name, session_string)
    try:
        await client.start()
        result = await fn(client)
        refreshed = await client.export_session_string()
        return result, (refreshed if refreshed != session_string else None)
    finally:
        await client.stop()


def _run(coro: Awaitable[T], *, timeout: float) -> T:
    async def guarded() -> T:
        return await asyncio.wait_for(coro, timeout=timeout)

    try:
        return asyncio.run(guarded())
    except Exception as exc:
        raise classify_error(exc) from exc


def run_join(*, session_name: str, session_string: str, target: str, probe_after: bool) -> JoinOutcome:
    ref = parse_target(target)
    timeout = float(settings.WORKER_ACTION_TIMEOUT_SECONDS)
    outcome, refreshed = _run(
        _with_client(session_name, session_string, lambda c: join_target(c, ref, probe_after=probe_after)), timeout=timeout * 4
    )
    return JoinOutcome(
        outcome.object_guid, outcome.object_type, outcome.title, outcome.member_count_before, outcome.member_count_after, refreshed
    )


def run_leave(*, session_name: str, session_string: str, target: str) -> LeaveOutcome:
    ref = parse_target(target)
    timeout = float(settings.WORKER_ACTION_TIMEOUT_SECONDS)
    outcome, refreshed = _run(_with_client(session_name, session_string, lambda c: leave_target(c, ref)), timeout=timeout * 4)
    return LeaveOutcome(outcome.object_guid, outcome.object_type, outcome.title, refreshed)


def run_view(*, session_name: str, session_string: str, target: str, service_id: str) -> ViewOutcome:
    ref = parse_target(target)
    timeout = float(settings.WORKER_ACTION_TIMEOUT_SECONDS)
    outcome, refreshed = _run(
        _with_client(session_name, session_string, lambda c: view_posts(c, ref, service_id=service_id)), timeout=timeout * 4
    )
    return ViewOutcome(outcome.object_guid, outcome.message_ids, refreshed)


__all__ = [
    "ActionError",
    "JoinOutcome",
    "LeaveOutcome",
    "ResolvedTarget",
    "ViewOutcome",
    "build_client",
    "classify_error",
    "client_kwargs",
    "join_target",
    "leave_target",
    "resolve_target",
    "run_join",
    "run_leave",
    "run_view",
    "view_posts",
    "worker_device_hash",
    "worker_user_agent",
]
