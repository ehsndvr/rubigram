#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from pathlib import Path

from rubigram import Client, filters
from rubigram.exceptions import InvalidInput
from rubigram.types.results import Message, RubinoPost, UrlFile

app = Client("test_client")


def _select_downloadable(post: RubinoPost) -> UrlFile | None:
    if getattr(post, "file", None) is not None:
        return post.file
    if getattr(post, "thumbnail", None) is not None:
        return post.thumbnail
    if getattr(post, "snapshot", None) is not None:
        return post.snapshot
    return None


async def _send_post_media(target_guid: str, post: RubinoPost, path: Path) -> None:
    caption = post.caption or "Powered by rubigram | ehsndvr"
    file_type = (post.file_type or "").lower()

    if file_type == "video":
        try:
            await app.send_video(
                object_guid=target_guid,
                path=path,
                text=caption,
                height=int(post.height or 0),
                width=int(post.width or 0),
                duration_ms=int((post.duration or 0) * 1000),
            )
            return
        except InvalidInput:
            print("send_video returned INVALID_INPUT, falling back to send_document")

    if file_type in {"image", "photo"}:
        try:
            await app.send_photo(
                object_guid=target_guid,
                path=path,
                text=caption,
                height=int(post.height or 0) or None,
                width=int(post.width or 0) or None,
            )
            return
        except InvalidInput:
            print("send_photo returned INVALID_INPUT, falling back to send_document")

    await app.send_document(
        object_guid=target_guid,
        path=path,
        text=caption,
    )


@app.on_message(filters.private & filters.rubino)
async def rubino_msg(c: Client, m: Message):
    res = await c.get_rubino_post(rubino_post_data=m.rubino_post_data)

    if res.post is None:
        return

    downloadable = _select_downloadable(res.post)
    if downloadable is None:
        await c.send_message(m.object_guid, "برای این پست فایل قابل دانلودی پیدا نشد.")
        return

    source_name = Path(downloadable.file_name or f"{res.post.id}.bin")
    tmp_name = Path(f"tmp_{res.post.id}{source_name.suffix or '.bin'}")
    try:
        downloaded_path = await downloadable.download(file_name=tmp_name.name)
        print(f"Downloaded file: {downloaded_path}")
        await _send_post_media(m.object_guid, res.post, Path(downloaded_path))
    finally:
        tmp_name.unlink(missing_ok=True)

async def main():
    print("* Bot Start ...")
    await app.start()
    await app.idle()

if __name__ == "__main__":
    asyncio.run(main())    
