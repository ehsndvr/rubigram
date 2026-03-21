from .send_message import SendMessage
from .send_video import SendVideo

class Messages (
    SendMessage,
    SendVideo
):
    pass
