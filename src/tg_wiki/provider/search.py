from typing import Optional

from tg_wiki.service.wiki_service import WikiService
from tg_wiki.domain.article import Article, ArticleMeta
from tg_wiki.cache.ports import Cache


class SearchProvide:
    def __init__(self, wiki: WikiService, cache: Cache):
        self._wiki = wiki
        self._cache = cache

    @property
    def wiki(self):
        return self._wiki

    @property
    def cache(self):
        return self._cache

    async def search_articles(self, query: str, *, limit: int = 5) -> list[ArticleMeta]:
        """
        Searches for articles matching the given query.

        Args:
            query: The search query string.
            limit: The maximum number of articles to return. Defaults to 5.

        Returns:
            A list of ArticleMeta objects matching the search criteria.
        """

        return await self.wiki.search_articles(query, limit=limit)

    async def get_arcticle_by_pageid(
        self, pageid: int, user_id: int
    ) -> Optional[Article]:
        """
        Retrieves an article by its page ID, utilizing cache for performance.

        Args:
            pageid (int): The unique identifier of the article page.
            user_id (int): The unique identifier of the user requesting the article.

        Returns:
            The Article object if found, otherwise None.
        """
        article = await self.cache.article_cache.get(pageid)
        if article:
            return article

        article = await self.wiki.get_article_by_pageid(pageid)
        if not article:
            return None

        await self.cache.article_cache.add(article)
        await self.cache.user_cache.add(user_id, pageid)
        return article
