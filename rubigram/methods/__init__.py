from .auth import AuthMethods
from .bots import Bots
from .chats import Chats
from .messages import Messages
from .medias import Medias
from .users import Users
from .utils import Utils

class Methods(
    AuthMethods,
    Users,
    Chats,
    Bots,
    Messages,
    Medias,
    Utils
):
    pass
