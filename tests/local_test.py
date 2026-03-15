import asyncio
from rubigram import Client


async def main():
    async with Client("my_account") as app:
        me = await app.get_me()
        print(me.user.first_name, me.user.user_guid)
        print(me.chat.status)
        # sent = await app.send_message(object_guid="u0DiqTP0d4d36e090fb7060d540a33c7", rnd="1", text="Hello from Rubigram!")
        # print(sent.message_update.message.text)


if __name__ == "__main__":
    asyncio.run(main())
