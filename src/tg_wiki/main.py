import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from dotenv import load_dotenv

from tg_wiki.client.http import HttpClient
from tg_wiki.service.wiki_service import WikiService
from tg_wiki.cache.ports import Cache
from tg_wiki.cache.in_memory.users import InMemoryUserCache
from tg_wiki.cache.in_memory.articles import InMemoryArticleCache
from tg_wiki.provider.reco import RecoProvide
from tg_wiki.provider.search import SearchProvide
from tg_wiki.bot.handlers import (
    cancel,
    default,
    help,
    next,
    noop,
    search,
    select,
    start,
)


async def main() -> None:
    load_dotenv()

    try:
        bot = Bot(token=os.environ["BOT_TOKEN"])
        dp = Dispatcher()

        http = HttpClient()
        await http.start()

        wiki_service = WikiService(http)
        cache = Cache(InMemoryUserCache(), InMemoryArticleCache())
        reco_provider = RecoProvide(wiki_service, cache)
        search_provider = SearchProvide(wiki_service, cache)
        dp.workflow_data["reco"] = reco_provider
        dp.workflow_data["search"] = search_provider

        dp.include_router(cancel.router)
        dp.include_router(start.router)
        dp.include_router(next.router)
        dp.include_router(select.router)
        dp.include_router(noop.router)
        dp.include_router(help.router)
        dp.include_router(search.router)
        dp.include_router(default.router)

        commands = [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Показать доступные команды"),
            BotCommand(command="next", description="Следующая статья"),
            BotCommand(command="search", description="Поиск статьи по запросу"),
            BotCommand(command="cancel", description="Отменить текущее действие"),
        ]
        await bot.set_my_commands(commands, BotCommandScopeDefault())

        await dp.start_polling(bot)
    finally:
        await http.close()
        await bot.session.close()


def run() -> None:
    asyncio.run(main())
