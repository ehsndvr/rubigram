"""Routes updates to handlers, honouring groups and propagation control."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .handler import ContinuePropagation, Handler, StopPropagation

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client
    from rubigram.types import Updates
    from rubigram.types.bot import InlineMessage, Update

log = logging.getLogger(__name__)


class Dispatcher:
    """Handler registry plus the fan-out logic for socket frames and bot updates.

    Handlers live in integer groups (default ``0``).  For each update kind the
    groups run in ascending order; inside a group the first handler whose
    filter matches runs and the group is done, unless the callback raises
    :class:`ContinuePropagation` (next handler in the same group) or
    :class:`StopPropagation` (nothing else runs for this update).
    Callback exceptions are logged and never stop the dispatcher.
    """

    def __init__(self, client: Client):
        self.client = client
        self.groups: Dict[int, List[Handler]] = defaultdict(list)

    # -- registry ------------------------------------------------------------

    def add_handler(self, handler: Handler, group: int = 0) -> Handler:
        self.groups[group].append(handler)
        return handler

    def remove_handler(self, handler: Handler, group: Optional[int] = None) -> bool:
        groups = [group] if group is not None else list(self.groups)
        for key in groups:
            handlers = self.groups.get(key, [])
            if handler in handlers:
                handlers.remove(handler)
                return True
        return False

    def handlers(self, kind: Optional[str] = None) -> List[Handler]:
        result: List[Handler] = []
        for key in sorted(self.groups):
            result.extend(h for h in self.groups[key] if kind is None or h.kind == kind)
        return result

    def has_handlers(self, kind: Optional[str] = None) -> bool:
        return bool(self.handlers(kind))

    # -- dispatch ------------------------------------------------------------

    async def dispatch(self, kind: str, update: Any) -> None:
        """Run the handlers registered for ``kind`` on ``update``."""
        for key in sorted(self.groups):
            for handler in list(self.groups[key]):
                if handler.kind != kind:
                    continue
                try:
                    matched = await handler.check(self.client, update)
                except Exception:
                    log.exception("Filter of %r failed", handler)
                    continue
                if not matched:
                    continue
                try:
                    await handler.invoke(self.client, update)
                except ContinuePropagation:
                    continue
                except StopPropagation:
                    return
                except Exception:
                    log.exception("Handler %r failed", handler)
                break

    async def dispatch_updates(self, updates: Updates) -> None:
        """Fan out one decrypted socket frame."""
        await self.dispatch("raw", updates)
        for message_update in updates.message_updates:
            message = message_update.message
            if message is None:
                continue
            action = message_update.action or "New"
            if action == "New":
                await self.dispatch("message", message)
            elif action == "Edit":
                await self.dispatch("edited_message", message)
            elif action == "Delete":
                await self.dispatch("deleted_message", message)
            else:
                await self.dispatch("message", message)
        for chat_update in updates.chat_updates:
            await self.dispatch("chat_update", chat_update)
        for activity in updates.show_activities:
            await self.dispatch("activity", activity)
        for notification in updates.show_notifications:
            await self.dispatch("notification", notification)
        for draft in updates.draft_message_updates:
            await self.dispatch("draft_update", draft)

    async def dispatch_bot_update(self, update: Update) -> None:
        """Fan out one Bot API update (polling or webhook)."""
        await self.dispatch("raw", update)
        kind = str(update.type or "")
        if kind in {"NewMessage", ""} and update.new_message is not None:
            message = update.new_message
            if getattr(message, "button_id", None):
                await self.dispatch("callback_query", message)
            await self.dispatch("message", message)
        elif kind == "UpdatedMessage" and update.updated_message is not None:
            await self.dispatch("edited_message", update.updated_message)
        elif kind == "RemovedMessage":
            await self.dispatch("deleted_message", update)

    async def dispatch_inline_message(self, inline_message: InlineMessage) -> None:
        await self.dispatch("inline_message", inline_message)
        if getattr(inline_message, "button_id", None):
            await self.dispatch("callback_query", inline_message)


__all__ = ["Dispatcher"]
