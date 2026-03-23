from .dialogs import Dialogs
from .bot_updates import BotUpdatesMethods
from .channels import Channels
from .groups import Groups


class Chats(Dialogs, BotUpdatesMethods, Channels, Groups):
    pass
