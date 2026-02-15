from typing import Protocol, Optional
from dataclasses import dataclass

from tg_wiki.domain.article import Article


class ArticleCache(Protocol):
    async def get(self, pageid: int) -> Optional[Article]:
        """
        Retrieves an article from the cache by its pageid.

        Args:
            pageid: The pageid of the article to retrieve.

        Returns:
            An Article object, or None if the article is not found in the cache.
        """
        ...

    async def add(self, article: Article) -> None:
        """
        Stores an article in the cache.

        Args:
            pageid: The pageid of the article to store.
            article: A dictionary containing the article's information to store in the cache.
        """
        ...


class UserCache(Protocol):
    async def get(self, user_id: int) -> list[int]:
        """
        Retrieves a list of recently viewed article pageids for a given user.

        Args:
            user_id: The user_id of the user to retrieve recent articles for.

        Returns:
            A list of article pageids that the user has recently viewed.
        """
        ...

    async def add(self, user_id: int, pageid: int) -> None:
        """
        Stores a pageid in the cache for a given user.

        Args:
            user_id: The user_id of the user to store the pageid for.
            pageid: The pageid to store in the cache.
        """
        ...


@dataclass
class Cache:
    user_cache: UserCache
    article_cache: ArticleCache
