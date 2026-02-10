import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from dotenv import load_dotenv

from src.tg_wiki.bot.handlers import next
from tg_wiki.bot.handlers import start
from tg_wiki.bot.handlers import search
from tg_wiki.bot.handlers import select
from tg_wiki.bot.handlers import noop
from tg_wiki.bot.handlers import help
from tg_wiki.bot.handlers import default


async def main() -> None:
    load_dotenv()

    bot = Bot(token=os.environ["BOT_TOKEN"])
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(next.router)
    dp.include_router(search.router)
    dp.include_router(select.router)
    dp.include_router(noop.router)
    dp.include_router(help.router)
    dp.include_router(default.router)

    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Показать доступные команды"),
        BotCommand(command="next", description="Следующая статья"),
        BotCommand(command="search", description="Найти статью по названию или ключевым словам"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
