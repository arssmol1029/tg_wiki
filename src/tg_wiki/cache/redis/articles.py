from typing import Optional

from tg_wiki.domain.article import Article
from .codec import dumps_article, loads_article


class RedisArticleCache:
    def __init__(self, redis, *, prefix: str = "tg_wiki", ttl: int = 24 * 3600) -> None:
        self._r = redis
        self._prefix = prefix
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self._ttl = ttl

    def _key(self, article: Article | int, *, lang: str = "ru") -> str:
        pageid = article if isinstance(article, int) else article.meta.pageid
        return f"{self._prefix}:article:{lang}:{int(pageid)}"

    async def get(self, pageid: int) -> Optional[Article]:
        key = self._key(pageid)
        raw = await self._r.get(key)
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return loads_article(raw)

    async def add(self, article: Article) -> None:
        key = self._key(article, lang=article.lang)
        val = dumps_article(article)
        await self._r.set(key, val, ex=self._ttl)
