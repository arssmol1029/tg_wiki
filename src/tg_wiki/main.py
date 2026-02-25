import asyncio
import os
import inspect
import redis.asyncio as redis

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from dotenv import load_dotenv

from tg_wiki.client.http import HttpClient
from tg_wiki.wiki_service.wiki import WikiService

from tg_wiki.cache.ports import Cache

from tg_wiki.cache.in_memory.last_view import InMemoryLastViewCache
from tg_wiki.cache.in_memory.articles import InMemoryArticleCache
from tg_wiki.cache.in_memory.user_settings import InMemoryUserSettingsCache
from tg_wiki.cache.in_memory.user_id import InMemoryUserIDCache

from tg_wiki.cache.redis.last_view import RedisLastViewCache
from tg_wiki.cache.redis.article import RedisArticleCache
from tg_wiki.cache.redis.user_settings import RedisUserSettingsCache
from tg_wiki.cache.redis.user_id import RedisUserIDCache

from tg_wiki.db.config import DBConfig
from tg_wiki.db.postgres.postgres import PostgresUserRepository

from tg_wiki.reco_service.reco import RecoService
from tg_wiki.search_service.search import SearchService
from tg_wiki.settings_service.user_settings import UserSettingsService

from tg_wiki.bot.handlers import (
    cancel,
    default,
    help,
    next,
    noop,
    search,
    select,
    start,
    settings,
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
                articles=RedisArticleCache(
                    redis_client,
                    prefix=prefix,
                    ttl=int(os.getenv("REDIS_ARTICLE_TTL_S", str(24 * 3600))),
                ),
                last_view=RedisLastViewCache(
                    redis_client,
                    prefix=prefix,
                    max_articles_per_user=int(os.getenv("REDIS_MAX_PER_USER", "20")),
                    ttl=int(os.getenv("REDIS_LASTVIEW_TTL_S", str(7 * 24 * 3600))),
                ),
                user_settings=RedisUserSettingsCache(
                    redis_client,
                    prefix=prefix,
                    ttl=int(os.getenv("REDIS_SETTINGS_TTL_S", str(24 * 3600))),
                ),
                user_ids=RedisUserIDCache(
                    redis_client,
                    prefix=prefix,
                    ttl=int(os.getenv("REDIS_USERID_TTL_S", str(24 * 3600))),
                ),
            )
        else:
            cache = Cache(
                InMemoryArticleCache(),
                InMemoryLastViewCache(),
                InMemoryUserSettingsCache(),
                InMemoryUserIDCache(),
            )

        reco_service = RecoService(wiki_service, cache)
        dp.workflow_data["reco_service"] = reco_service

        search_service = SearchService(wiki_service, cache)
        dp.workflow_data["search_service"] = search_service

        user_repo = PostgresUserRepository(DBConfig.from_env())
        await user_repo.start()
        settings_service = UserSettingsService(user_repo, cache)
        dp.workflow_data["settings_service"] = settings_service

        dp.include_router(cancel.router)
        dp.include_router(start.router)
        dp.include_router(next.router)
        dp.include_router(select.router)
        dp.include_router(noop.router)
        dp.include_router(help.router)
        dp.include_router(search.router)
        dp.include_router(settings.router)
        dp.include_router(default.router)

        commands = [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Показать доступные команды"),
            BotCommand(command="next", description="Следующая статья"),
            BotCommand(command="search", description="Поиск статьи по запросу"),
            BotCommand(command="settings", description="Изменить настройки"),
            BotCommand(command="cancel", description="Отменить текущее действие"),
        ]
        await bot.set_my_commands(commands, BotCommandScopeDefault())

        await dp.start_polling(bot)

    finally:
        if http is not None:
            await http.close()
        if redis_client is not None:
            await _close_redis(redis_client)
        if user_repo is not None:
            await user_repo.close()
        if bot is not None:
            await bot.session.close()


def run() -> None:
    asyncio.run(main())
