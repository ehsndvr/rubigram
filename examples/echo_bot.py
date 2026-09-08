"""A Bot API echo bot.

Run with the token from @BotFather-equivalent (Rubika's bot panel) in the
``RUBIGRAM_BOT_TOKEN`` environment variable::

    RUBIGRAM_BOT_TOKEN=... python examples/echo_bot.py
"""

import os

from rubigram import Client, filters

app = Client("echo_bot", token=os.environ["RUBIGRAM_BOT_TOKEN"])


@app.on_message(filters.command("start"))
async def start(client: Client, message):
    await message.reply("Hi! Send me any text and I will echo it back.")


@app.on_message(filters.text & ~filters.command("start"))
async def echo(client: Client, message):
    await message.reply(message.text)


if __name__ == "__main__":
    app.run()
