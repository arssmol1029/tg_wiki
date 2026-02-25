from typing import Protocol, Optional
from dataclasses import dataclass

from tg_wiki.domain.article import Article
from tg_wiki.domain.user import UserSettings


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

    async def update(self, article: Article) -> None:
        """
        Stores an article in the cache.

        Args:
            pageid: The pageid of the article to store.
            article: A dictionary containing the article's information to store in the cache.
        """
        ...


class LastViewCache(Protocol):
    async def get(self, user_id: int) -> list[int]:
        """
        Retrieves a list of recently viewed article pageids for a given user.

        Args:
            user_id: The user_id of the user to retrieve recent articles for.

        Returns:
            A list of article pageids that the user has recently viewed.
        """
        ...

    async def update(self, user_id: int, pageid: int) -> None:
        """
        Stores a pageid in the cache for a given user.

        Args:
            user_id: The user_id of the user to store the pageid for.
            pageid: The pageid to store in the cache.
        """
        ...


class UserSettingsCache(Protocol):
    async def get(self, user_id: int) -> Optional[UserSettings]:
        """
        Retrieves user settings.

        Args:
            user_id: The user_id of the user to retrieve settings.

        Returns:
            User settings object.
        """
        ...

    async def update(self, user_id: int, settings: UserSettings) -> None:
        """
        Stores a settings for a given user.

        Args:
            user_id: The user_id of the user to store settings for.
            settings: The user Settings object.
        """


class UserIDCache(Protocol):
    async def get(self, provider: str, external_id: int) -> Optional[int]:
        """
        Retrieves user settings.

        Args:
            user_id: The user_id of the user to retrieve settings.

        Returns:
            User settings object.
        """
        ...

    async def update(self, user_id: int, provider: str, external_id: int) -> None:
        """
        Stores a settings for a given user.

        Args:
            user_id: The user_id of the user to store settings for.
            settings: The user Settings object.
        """


@dataclass
class Cache:
    articles: ArticleCache
    last_view: LastViewCache
    user_settings: UserSettingsCache
    user_ids: UserIDCache
