from .guess_upload_mime import GuessUploadMime
from .request_send_files import RequestSendFiles

class Utils(
    GuessUploadMime,
    RequestSendFiles
):
    pass