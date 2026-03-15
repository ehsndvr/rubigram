import rubigram


class ChatAvatar(Object):
    """A chat avatar.

    Parameters:
        small_file_id (``str``):
            File identifier of small (160x160) chat photo.
            This file_id can be used only for photo download and only for as long as the photo is not changed.

        small_photo_unique_id (``str``):
            Unique file identifier of small (160x160) chat photo, which is supposed to be the same over time and for
            different accounts. Can't be used to download or reuse the file.

        big_file_id (``str``):
            File identifier of big (640x640) chat photo.
            This file_id can be used only for photo download and only for as long as the photo is not changed.

        big_photo_unique_id (``str``):
            Unique file identifier of big (640x640) chat photo, which is supposed to be the same over time and for
            different accounts. Can't be used to download or reuse the file.
    """
    
    def __init__(
        self,
        *,
        client: "rubigram.Client" = None
        
    ):
        super().__init__(client)
        
        