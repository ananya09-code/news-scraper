import asyncio
from teleglance import TeleGlanceClient


async def main():
    async with TeleGlanceClient() as client:
        channel = await client.get_channel("tikvahethiopia")

        print("Channel:", channel.title)
        print("Subscribers:", channel.counts.subscribers)

        async for msg in client.iter_messages(
            "tikvahethiopia",
            limit=100,
        ):
            print(f"[{msg.id}] {msg.text}")


asyncio.run(main())
