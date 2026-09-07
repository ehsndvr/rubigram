"""Fetch a Rubino post by id or from a shared post inside a chat."""

import asyncio

from rubigram import Client, filters

app = Client("my_account")


@app.on_message(filters.rubino)
async def handle_rubino_post(client: Client, message):
    result = await client.get_rubino_post(rubino_post_data=message.rubino_post_data)
    if result.post is not None:
        print(result.post.caption, result.post.share_url)
        await result.post.download()  # saves <post_id>.<ext> in the working directory


async def main() -> None:
    async with app:
        # Both ids come from a post's share link or from message.rubino_post_data.
        result = await app.get_rubino_post(post_id="<post_id>", post_profile_id="<profile_id>")
        print(result.post)
        await app.idle()


if __name__ == "__main__":
    asyncio.run(main())
