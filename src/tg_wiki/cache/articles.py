from typing import Protocol, Optional

from tg_wiki.domain.article import Article


class ArticleCache(Protocol):
    async def get(self, pageid: str) -> Optional[Article]:
        """
        Retrieves an article from the cache by its pageid.

        Args:
            pageid: The pageid of the article to retrieve.

        Returns:
            An Article object, or None if the article is not found in the cache.
        """
        ...

    async def add(self, pageid: str, article: Article) -> None:
        """
        Stores an article in the cache.

        Args:
            pageid: The pageid of the article to store.
            article: A dictionary containing the article's information to store in the cache.
        """
        ...
