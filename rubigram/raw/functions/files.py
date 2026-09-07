"""``file_inline`` construction and upload mime guessing."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional

_SHORT_MIMES = {"ogg", "mp4", "jpg", "jpeg", "png", "zip", "mp3", "gif", "webp", "pdf", "apk"}


def guess_upload_mime(path: "str | Path") -> str:
    """The ``mime`` value Rubika expects in ``requestSendFile``: the file extension.

    The web client sends the extension (``getExt``), not a MIME type; a real
    MIME type is only used when the extension is unknown.
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower().lstrip(".")
    if suffix in _SHORT_MIMES:
        return "jpg" if suffix == "jpeg" else suffix
    if suffix:
        return suffix
    guessed, _ = mimetypes.guess_type(file_path.name)
    return guessed or "bin"


def build_file_inline(
    *,
    file_id: Any,
    dc_id: Any,
    access_hash_rec: Any,
    file_name: str,
    size: int,
    media_type: str,
    mime: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[float] = None,
    thumb_inline: Optional[str] = None,
    is_round: Optional[bool] = None,
    is_spoil: Optional[bool] = None,
    music_performer: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """The ``file_inline`` block of ``sendMessage`` for an uploaded file."""
    block: Dict[str, Any] = {
        "file_name": file_name,
        "size": size,
        "type": media_type,
        "dc_id": dc_id,
        "file_id": file_id,
        "mime": mime,
        "access_hash_rec": access_hash_rec,
    }
    if width is not None:
        block["width"] = width
    if height is not None:
        block["height"] = height
    if duration_ms is not None:
        block["time"] = duration_ms
    if thumb_inline is not None:
        block["thumb_inline"] = thumb_inline
    if is_round is not None:
        block["is_round"] = is_round
    if is_spoil is not None:
        block["is_spoil"] = is_spoil
    if music_performer is not None:
        block["music_performer"] = music_performer
    if extra:
        block.update({key: value for key, value in extra.items() if value is not None})
    return block


__all__ = ["guess_upload_mime", "build_file_inline"]
