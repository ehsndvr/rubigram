import asyncio

from rubigram import Client, filters

app = Client("my_account")


@app.on_message(filters.rubino)
async def handle_rubino_post(client, message):
    post = await client.get_rubino_post(rubino_post_data=message.rubino_post_data)
    print(post.post)


async def main():
    await app.start()

    result = await app.get_rubino_post(
        post_id="69b06fee3b7750514a649aa7",
        post_profile_id="5f325f3c9dc6d60882e054b2",
    )
    print(result.post)

    await app.idle()


if __name__ == "__main__":
    asyncio.run(main())
