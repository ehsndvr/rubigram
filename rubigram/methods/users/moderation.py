from __future__ import annotations

from typing import Any

import rubigram
from rubigram.raw.methods import BlockUser, UnblockUser
from rubigram.types import RawObject


class UserModeration:
    async def block_user(self: "rubigram.Client", object_guid: Any = None, *, peer: Any = None) -> RawObject:
        return await self.invoke(BlockUser(object_guid=self._resolve_user_guid(peer or object_guid)))

    async def unblock_user(self: "rubigram.Client", object_guid: Any = None, *, peer: Any = None) -> RawObject:
        return await self.invoke(UnblockUser(object_guid=self._resolve_user_guid(peer or object_guid)))
