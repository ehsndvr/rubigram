"""Reply to every shared Rubino post with the downloaded media (user session)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rubigram import Client, filters
from rubigram.errors import InvalidInput
from rubigram.types import Message, RubinoPost, UrlFile

app = Client("rubino_downloader")


def select_downloadable(post: RubinoPost) -> UrlFile | None:
    return post.file or post.thumbnail or post.snapshot


async def send_post_media(target_guid: str, post: RubinoPost, path: Path) -> None:
    caption = post.caption or "Powered by rubigram"
    file_type = (post.file_type or "").lower()

    if file_type == "video":
        try:
            await app.send_video(
                target_guid,
                path,
                text=caption,
                height=int(post.height or 0),
                width=int(post.width or 0),
                duration_ms=int((post.duration or 0) * 1000),
            )
            return
        except InvalidInput:
            print("send_video returned INVALID_INPUT, falling back to send_document")

    if file_type in {"image", "picture", "photo"}:
        try:
            await app.send_photo(target_guid, path, text=caption, height=int(post.height or 0) or None, width=int(post.width or 0) or None)
            return
        except InvalidInput:
            print("send_photo returned INVALID_INPUT, falling back to send_document")

    await app.send_document(target_guid, path, text=caption)


@app.on_message(filters.private & filters.rubino)
async def on_rubino_post(client: Client, message: Message):
    result = await client.get_rubino_post(rubino_post_data=message.rubino_post_data)
    post = result.post
    if post is None:
        return

    downloadable = select_downloadable(post)
    if downloadable is None:
        await message.reply("No downloadable file was found for this post.")
        return

    source_name = Path(downloadable.file_name or f"{post.id}.bin")
    tmp_path = Path(f"tmp_{post.id}{source_name.suffix or '.bin'}")
    try:
        downloaded = await downloadable.download(file_name=tmp_path.name)
        print("downloaded", downloaded)
        await send_post_media(message.object_guid or "", post, Path(downloaded))
    finally:
        tmp_path.unlink(missing_ok=True)


async def main() -> None:
    print("* bot started")
    async with app:
        await app.idle()


if __name__ == "__main__":
    asyncio.run(main())
