"""Active sessions and the portable session string."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from rubigram.raw.methods import ActionOnUnconfirmedSession, GetMySessions, GetUnconfirmedSessions, TerminateOtherSessions, TerminateSession
from rubigram.types import Empty, MySessions, UnconfirmedSessions

if TYPE_CHECKING:  # pragma: no cover
    from rubigram.client.client import Client


class Sessions:
    async def get_my_sessions(self: "Client") -> MySessions:
        """Active sessions of the account (``getMySessions``). [HTTP]"""
        return await self.invoke(GetMySessions())

    async def terminate_session(self: "Client", session_key: str) -> Empty:
        """Log another device out (``terminateSession``). [HTTP]"""
        return await self.invoke(TerminateSession(session_key=session_key))

    async def terminate_other_sessions(self: "Client") -> Empty:
        """Log every other device out (``terminateOtherSessions``). [HTTP]"""
        return await self.invoke(TerminateOtherSessions())

    async def get_unconfirmed_sessions(self: "Client") -> UnconfirmedSessions:
        return await self.invoke(GetUnconfirmedSessions())

    async def action_on_unconfirmed_session(self: "Client", unconfirmed_session_key: str, action: str) -> Empty:
        return await self.invoke(ActionOnUnconfirmedSession(unconfirmed_session_key=unconfirmed_session_key, action=str(getattr(action, "value", action))))

    async def confirm_session(self: "Client", unconfirmed_session_key: str) -> Empty:
        return await self.action_on_unconfirmed_session(unconfirmed_session_key, "Accept")

    async def reject_session(self: "Client", unconfirmed_session_key: str) -> Empty:
        return await self.action_on_unconfirmed_session(unconfirmed_session_key, "Reject")

    # -- session string ------------------------------------------------------

    async def export_session_string(self: "Client") -> str:
        """Portable session string (contains the auth key; treat it as a secret)."""
        if not self.storage.is_open:
            await self.storage.open()
        return await self.storage.export_session_string()

    async def import_session_string(self: "Client", session_string: str) -> None:
        """Load a session string into this client's storage."""
        if not self.storage.is_open:
            await self.storage.open()
        await self.storage.import_session_string(session_string)

    async def export_session_dict(self: "Client") -> dict[str, Any]:
        if not self.storage.is_open:
            await self.storage.open()
        return await self.storage.export_session_dict()

    @property
    def user_guid(self: "Client") -> Optional[str]:
        """The logged-in user's guid when known without a storage round trip."""
        return getattr(self, "_cached_user_guid", None)


__all__ = ["Sessions"]
