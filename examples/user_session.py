"""A phone-number (user) session: first login, then react to private messages.

The first run asks for the verification code through ``code_callback``; the
session is stored in ``my_account.session`` next to this script, so later runs
start without any prompt.  Set ``RUBIGRAM_PHONE`` to skip the phone prompt.
"""

import asyncio
import os

from rubigram import Client, filters
from rubigram.types import Message, SentCode


async def ask_code(sent: SentCode) -> str:
    """Called once per login attempt with the ``sendCode`` result."""
    return await asyncio.to_thread(input, f"Code sent by {sent.send_type or 'SMS'} ({sent.code_digits_count or 5} digits): ")


app = Client("my_account", phone_number=os.environ.get("RUBIGRAM_PHONE"), code_callback=ask_code)


@app.on_message(filters.text & filters.private & ~filters.me)
async def on_private_text(client: Client, message: Message):
    print(f"{message.author_object_guid}: {message.text}")
    await message.reply("received", parse_mode="markdown")


async def main() -> None:
    async with app:
        me = await app.get_me()
        print("logged in as", me.user.first_name, me.user.user_guid)
        page = await app.get_chats()
        for chat in page.chats[:5]:
            print(chat.object_guid, chat.type, chat.count_unseen)
        await app.idle()


if __name__ == "__main__":
    asyncio.run(main())
