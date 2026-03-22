import mimetypes
from pathlib import Path

import rubigram


class GuessUploadMime:
    def guess_upload_mime(
        self: "rubigram.Client",
        path: Path,
    ) -> str:
        guessed, _ = mimetypes.guess_type(path.name)
        if guessed:
            suffix = path.suffix.lower().lstrip(".")
            if suffix in {"ogg", "mp4", "jpg", "jpeg", "png", "zip", "mp3"}:
                return "jpg" if suffix == "jpeg" else suffix
            return guessed
        suffix = path.suffix.lower().lstrip(".")
        return suffix or "bin"
