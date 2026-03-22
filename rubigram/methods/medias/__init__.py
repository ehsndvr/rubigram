from .send_uploaded_media import SendUploadedMedia
from .upload_file import UploadMedia
from .media_shortcuts import MediaShortcuts

class Medias (
    MediaShortcuts,
    SendUploadedMedia,
    UploadMedia
):
    pass
