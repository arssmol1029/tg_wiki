from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence, Iterable

from rec_service.domain.vector import VECTOR_DIM


def zero_vec() -> list[float]:
    return [0.0] * VECTOR_DIM


@dataclass(frozen=True, slots=True)
class ArticleInsert:
    """
    Represents an article payload to be inserted.

    Note:
        `embedding` must match the configured embedding dimension.
    """

    pageid: int
    title: str
    lang: str
    url: str
    thumbnail_url: str
    extract: str
    extract_len: int
    embedding: list[float]


@dataclass(frozen=True, slots=True)
class ArticleRow:
    """
    Represents a stored article row returned by the database layer.
    """

    article_id: int
    is_active: bool
    lang: str
    pageid: int
    title: str
    url: str
    thumbnail_url: str
    extract: str
    extract_len: int
    created_at: datetime
    updated_at: datetime


class UserRepo(Protocol):
    async def create_user(
        self, *, user_id: int, pref: list[float] | None, calibration_size: int
    ) -> bool:
        """
        Add a new user to the database.

        Args:
            user_id: The unique identifier of the user to be created.
            pref: User preference vector. If None set zero vector.
            calibration_size: Size of inserted user calibration pool

        Returns:
            True if the user was successfully created, False otherwise.
        """
        ...

    async def get_user_pref(self, *, user_id: int) -> list[float] | None:
        """
        Retrieve user preference vector.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            User preference vector or None if user or his preference not found.
        """
        ...

    async def get_user_calibration_size(self, *, user_id: int) -> int | None:
        """
        Returns:
            User calibration size or None if user not found.
        """
        ...

    async def get_user_total_seen(self, *, user_id: int) -> int | None:
        """
        Returns:
            User total seen articles field value or None if user not found.
        """
        ...

    async def update_user_pref(self, *, user_id: int, pref: list[float]) -> bool:
        """
        Update user preference vector.

        Args:
            user_id: The unique identifier of the user.
            pref: The preference vector to be updated.

        Returns:
            True if the user preference was successfully updated, False otherwise.
        """
        ...

    async def reset_user(self, *, user_id: int, calibration_size: int) -> bool:
        """
        Reset user preference.

        Args:
            user_id: The unique identifier of the user to be added.
            calibration_size: Size of inserted user calibration pool size.

        Returns:
            True if the user preference was successfully reseted, False otherwise.
        """
        ...

    async def delete_user(self, *, user_id: int) -> bool:
        """
        Delete user

        Args:
            user_id: The unique identifier of the user to be deleted.

        Returns:
            True if the user was successfully deleted or not exists, False otherwise.
        """
        ...

    async def get_max_user_seen(self, *, lang: str) -> list[int]:
        """
        Returns pageids of articles viewed by the most active user (with the most records in user_seen_articles)
        in descending order of the total number of views on them.

        Returns:
            List of selected pageids.
        """
        ...


class PoolRepo(Protocol):
    async def add_articles(
        self, *, articles: Sequence[ArticleInsert], is_active: bool = True
    ) -> list[int]:
        """
        Add articles.

        Returns:
            List of inserted articles pageids
        """
        ...

    async def add_article(
        self, *, article: ArticleInsert, is_active: bool = True
    ) -> bool:
        """
        Add article.

        Returns:
            True if article was added, otherwise False
        """
        ...

    async def get_articles_by_pageids(
        self, *, lang: str, pageids: Sequence[int]
    ) -> list[ArticleRow]:
        """
        Return articles by (lang, pageid).

        Args:
            lang: Language code.
            pageids: Sequence of Wikipedia page id.

        Returns:
            List of articles.
        """
        ...

    async def get_article_by_pageid(
        self, *, lang: str, pageid: int
    ) -> ArticleRow | None:
        """
        Return article by (lang, pageid).

        Args:
            lang: Language code.
            pageid: Wikipedia page id.

        Returns:
            Article or None if not found.
        """
        ...

    async def get_best_articles(
        self, *, lang: str, pref: list[float], count: int, min_length: int = 0
    ) -> list[ArticleRow]:
        """
        Return top-count best matching articles by the preference vector.

        Args:
            lang: Language code.
            preference: Preference embedding. Dimension must match stored embedding dimension.
            count: Number of articles to return.
            min_length: Minimal length of returned article

        Returns:
            List of up to count articles ordered by similarity (best first).
        """
        ...

    async def get_active_articles_count(self, *, lang: str) -> int:
        """
        Args:
            lang: Language code.

        Returns:
            Count of active articles
        """
        ...

    async def get_inactive_articles_count(self, *, lang: str) -> int:
        """
        Args:
            lang: Language code.

        Returns:
            Count of inactive articles
        """
        ...

    async def set_articles_active(
        self, *, lang: str, pageids: Iterable[int], is_active: bool = False
    ) -> bool:
        """
        Updates article is_active field.

        Args:
            lang: Language code.
            pageids: Iterable object of Wikipedia page id.
            is_active: Value to replace article activity

        Returns:
            True if the article activity was successfully updated, False otherwise.
        """
        ...

    async def get_article_embedding(
        self, *, lang: str, pageid: int
    ) -> list[float] | None:
        """
        Return article embedding.

        Args:
            lang: Language code.
            pageid: Wikipedia page id.

        Returns:
            Article embedding or None if not found.
        """
        ...

    async def delete_articles(self, *, lang: str, pageids: Iterable[int]) -> int:
        """
        Delete articles by (lang, pageid).

        Args:
            lang: Language code.
            pageids: Iterable object of Wikipedia page id.

        Returns:
            Count of deleted articles
        """
        ...

    async def delete_article(self, *, lang: str, pageid: int) -> bool:
        """
        Delete article by (lang, pageid).

        Args:
            lang: Language code.
            pageid: Wikipedia page id.

        Returns:
            True if article was deleted, otherwhise False
        """
        ...

    async def delete_articles_by_time(self, *, lang: str, count: int) -> int:
        """
        Delete the count oldest articles.

        Args:
            lang: Language code.
            count: Count of articles to delete.

        Returns:
            Count of deleted articles
        """
        ...


class QuarantineRepo(Protocol):
    async def filter_not_quarantined(
        self, *, lang: str, pageids: Iterable[int]
    ) -> set[int]:
        """
        Return the subset of pageids that are NOT present in quarantine for the given lang.

        Args:
            lang: Language code.
            pageids: Iterable object of Wikipedia page id.

        Returns:
            Set of pageids that are not quarantined.
        """
        ...

    async def add_articles(self, *, lang: str, pageids: Iterable[int]) -> int:
        """
        Add articles into quarantine.

        Args:
            lang: Language code.
            pageids: List of pageids of articles.

        Returns:
            Number of inserted/updated quarantine rows.
        """
        ...

    async def release_by_time(self, *, deadline: datetime) -> int:
        """
        Release quarantine entries inserted not later than the given deadline.

        Args:
            deadline: All rows with inserted_at <= deadline will be deleted.

        Returns:
            Number of deleted rows.
        """
        ...


class Uow(Protocol):
    users: UserRepo
    pool: PoolRepo
    quarantine: QuarantineRepo

    async def __aenter__(self) -> "Uow": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
