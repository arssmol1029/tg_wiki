from tg_wiki.service.wiki_service import WikiService
from tg_wiki.domain.article import Article
from tg_wiki.cache.ports import Cache


class RecoProvide:
    def __init__(self, wiki: WikiService, cache: Cache):
        self._wiki = wiki
        self._cache = cache

    @property
    def wiki(self):
        return self._wiki

    @property
    def cache(self):
        return self._cache

    async def get_next_arcticle(self, user_id: int) -> Article:
        """
        Retrieve the next article for a user, utilizing cache for performance.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            A randomly selected article that is not in the user's recent history.
        """

        last_articles = await self.cache.user_cache.get(user_id)

        while True:
            article = await self.wiki.get_random_article()
            if not article:
                continue

            pageid = article.meta.pageid
            if pageid not in last_articles:
                await self.cache.user_cache.add(user_id, pageid)
                await self.cache.article_cache.add(article)
                return article
