from .send_message import SendMessage
from .send_video import SendVideo
from .manage_message import ManageMessage

class Messages (
    SendMessage,
    SendVideo,
    ManageMessage
):
    pass
