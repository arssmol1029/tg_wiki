import asyncio
import os
import inspect
import redis.asyncio as redis

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from dotenv import load_dotenv

from tg_wiki.client.http import HttpClient
from tg_wiki.service.wiki_service import WikiService

from tg_wiki.cache.ports import Cache
from tg_wiki.cache.in_memory.users import InMemoryUserCache
from tg_wiki.cache.in_memory.articles import InMemoryArticleCache
from tg_wiki.cache.redis.users import RedisUserCache
from tg_wiki.cache.redis.articles import RedisArticleCache

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


async def _close_redis(r) -> None:
    if r is None:
        return
    for name in ("aclose", "close"):
        fn = getattr(r, name, None)
        if fn:
            res = fn()
            if inspect.isawaitable(res):
                await res
            break
    pool = getattr(r, "connection_pool", None)
    if pool is not None and hasattr(pool, "disconnect"):
        res = pool.disconnect()
        if inspect.isawaitable(res):
            await res


async def main() -> None:
    load_dotenv()

    redis_client = None
    http = None
    bot = None

    try:
        bot = Bot(token=os.environ["BOT_TOKEN"])
        dp = Dispatcher()

        http = HttpClient()
        await http.start()

        wiki_service = WikiService(http)

        cache_type = os.getenv("CACHE_BACKEND", "in-memory")
        if cache_type == "redis":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            prefix = os.getenv("REDIS_PREFIX", "tg_wiki")

            redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            cache = Cache(
                user_cache=RedisUserCache(
                    redis_client,
                    prefix=prefix,
                    max_articles_per_user=int(os.getenv("REDIS_MAX_PER_USER", "20")),
                    ttl=int(os.getenv("REDIS_USER_TTL_S", str(7 * 24 * 3600))),
                ),
                article_cache=RedisArticleCache(
                    redis_client,
                    prefix=prefix,
                    ttl=int(os.getenv("REDIS_ARTICLE_TTL_S", str(24 * 3600))),
                ),
            )
        else:
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
        if http is not None:
            await http.close()
        if redis_client is not None:
            await _close_redis(redis_client)
        if bot is not None:
            await bot.session.close()


def run() -> None:
    asyncio.run(main())
