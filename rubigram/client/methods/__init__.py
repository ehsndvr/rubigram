"""Every public method of :class:`~rubigram.Client`, grouped by domain into mixins."""

from .advanced import Advanced
from .auth import Auth
from .bot_api import BotApi
from .channels import Channels
from .chats import Chats
from .groups import Groups
from .join_links import JoinLinksMixin
from .media import Media
from .messages import Messages
from .rubino import Rubino
from .services import Services
from .sessions import Sessions
from .settings import Settings
from .stickers import Stickers
from .updates import UpdatesMixin
from .users import Users


class Methods(
    Auth,
    Sessions,
    Users,
    Chats,
    Messages,
    Media,
    Groups,
    Channels,
    JoinLinksMixin,
    Stickers,
    Settings,
    Services,
    Rubino,
    BotApi,
    UpdatesMixin,
    Advanced,
):
    """Aggregated mixin; :class:`~rubigram.Client` inherits every public method from here."""


__all__ = ["Methods"]
