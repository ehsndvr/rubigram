"""Deprecated module name: the update-related RPCs live in ``chats``, ``users`` and ``messages``."""

from rubigram.raw.methods.chats import GetChatsUpdates
from rubigram.raw.methods.messages import GetAvailableReactions
from rubigram.raw.methods.users import GetContactsUpdates

__all__ = ["GetChatsUpdates", "GetContactsUpdates", "GetAvailableReactions"]
