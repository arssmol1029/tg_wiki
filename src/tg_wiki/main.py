import asyncio
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from src.tg_wiki.bot.handlers import next
from tg_wiki.bot.handlers import start
from tg_wiki.bot.handlers import search


async def main() -> None:
    load_dotenv()

    bot = Bot(token=os.environ["BOT_TOKEN"])
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(next.router)
    dp.include_router(search.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
