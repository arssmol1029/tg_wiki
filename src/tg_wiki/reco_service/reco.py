import asyncio

from dataclasses import dataclass

from tg_wiki.wiki_service.wiki import WikiService
from tg_wiki.domain.article import Article
from tg_wiki.cache.ports import Cache


@dataclass
class RecoService:

    _wiki: WikiService
    _cache: Cache

    @property
    def wiki(self) -> WikiService:
        return self._wiki

    @property
    def cache(self) -> Cache:
        return self._cache

    async def get_next_article(self, user_id: int) -> Article:
        """
        Retrieve the next article for a user, utilizing cache for performance.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            A randomly selected article that is not in the user's recent history.
        """
        last_articles = await self.cache.last_view.get(user_id) or ()

        while True:
            article = await self.wiki.get_random_article()
            if not article or not article.meta:
                continue

            pageid = article.meta.pageid
            if not pageid:
                continue

            if pageid not in last_articles:
                await self.cache.last_view.update(user_id, pageid)
                asyncio.create_task(self.cache.articles.update(article))
                return article
