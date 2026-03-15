import asyncio
from rubigram import Client, filters

app = Client("my_account")


@app.on_message(filters.text & filters.private & ~filters.me)
async def handle_message(client, message):
    print(message.text)
    await message.reply("Hello from Rubigram!")


async def main():
    print("start rubigram, wait for your texts")
    await app.start()
    await app.idle()


if __name__ == "__main__":
    asyncio.run(main())
