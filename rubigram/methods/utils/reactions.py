import rubigram
from rubigram.raw.methods import GetAvailableReactions
from rubigram.types import AvailableReactions


class Reactions:
    async def get_available_reactions(self: "rubigram.Client") -> AvailableReactions:
        return await self.invoke(GetAvailableReactions())
