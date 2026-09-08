"""Active sessions and the portable session string."""

from __future__ import annotations

from typing import Any, Optional

from rubigram.client.base import BaseClient
from rubigram.raw.methods import ActionOnUnconfirmedSession, GetMySessions, GetUnconfirmedSessions, TerminateOtherSessions, TerminateSession
from rubigram.types import Empty, MySessions, UnconfirmedSessions


class Sessions(BaseClient):
    async def get_my_sessions(self) -> MySessions:
        """Active sessions of the account (``getMySessions``). [HTTP]"""
        return await self.invoke(GetMySessions())

    async def terminate_session(self, session_key: str) -> Empty:
        """Log another device out (``terminateSession``). [HTTP]"""
        return await self.invoke(TerminateSession(session_key=session_key))

    async def terminate_other_sessions(self) -> Empty:
        """Log every other device out (``terminateOtherSessions``). [HTTP]"""
        return await self.invoke(TerminateOtherSessions())

    async def get_unconfirmed_sessions(self) -> UnconfirmedSessions:
        """Login attempts waiting for confirmation (``getUnconfirmedSessions``). [HTTP]"""
        return await self.invoke(GetUnconfirmedSessions())

    async def action_on_unconfirmed_session(self, unconfirmed_session_key: str, action: str) -> Empty:
        """Accept or reject a login attempt from another device (``actionOnUnconfirmedSession``). [HTTP]"""
        return await self.invoke(
            ActionOnUnconfirmedSession(unconfirmed_session_key=unconfirmed_session_key, action=str(getattr(action, "value", action)))
        )

    async def confirm_session(self, unconfirmed_session_key: str) -> Empty:
        """Accept a login attempt from another device. [HTTP]"""
        return await self.action_on_unconfirmed_session(unconfirmed_session_key, "Accept")

    async def reject_session(self, unconfirmed_session_key: str) -> Empty:
        """Reject a login attempt from another device. [HTTP]"""
        return await self.action_on_unconfirmed_session(unconfirmed_session_key, "Reject")

    # -- session string ------------------------------------------------------

    async def export_session_string(self) -> str:
        """Portable session string (contains the auth key; treat it as a secret)."""
        if not self.storage.is_open:
            await self.storage.open()
        return await self.storage.export_session_string()

    async def import_session_string(self, session_string: str) -> None:
        """Load a session string into this client's storage."""
        if not self.storage.is_open:
            await self.storage.open()
        await self.storage.import_session_string(session_string)

    async def export_session_dict(self) -> dict[str, Any]:
        """The session as a plain dict (``auth``, ``user_guid``, keys, DC configuration). [HTTP]"""
        if not self.storage.is_open:
            await self.storage.open()
        return await self.storage.export_session_dict()

    @property
    def user_guid(self) -> Optional[str]:
        """The logged-in user's guid when known without a storage round trip."""
        return getattr(self, "_cached_user_guid", None)


__all__ = ["Sessions"]
