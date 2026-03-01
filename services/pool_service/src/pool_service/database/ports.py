from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ShardRef:
    """
    Identifies a concrete shard generation.
    """

    lang: str
    shard_id: int
    shard_gen: int


@dataclass(frozen=True, slots=True)
class ArticleInsert:
    """
    Represents an article payload to be inserted into a shard generation.

    Note:
        `embedding` must match the configured embedding dimension.
    """

    pageid: int
    title: str
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
    lang: str
    pageid: int
    shard_id: int
    shard_gen: int
    shift: int
    title: str
    url: str
    thumbnail_url: str
    extract: str
    extract_len: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ShardRow:
    """
    Represents a shard generation row.
    """

    lang: str
    shard_id: int
    shard_gen: int
    shard_size: int
    created_at: datetime


class PoolRepo(Protocol):
    async def get_article(self, *, lang: str, pageid: int) -> ArticleRow | None:
        """
        Returns an article by (lang, pageid).

        Args:
            lang: Language code.
            pageid: Wikipedia page id.

        Returns:
            ArticleRow if present, otherwise None.
        """
        ...

    async def get_best_articles(
        self,
        *,
        lang: str,
        preference: list[float],
        count: int,
    ) -> list[ArticleRow]:
        """
        Returns top-k best matching articles by the preference vector.

        Args:
            lang: Language code.
            preference: Preference embedding. Dimension must match stored embedding dimension.
            k: Number of articles to return.

        Returns:
            A list of up to k articles ordered by similarity (best first).
        """
        ...

    async def add_shard(
        self,
        *,
        lang: str,
        articles: Sequence[ArticleInsert],
    ) -> ShardRef:
        """
        Adds a new shard generation for the given language.

        Args:
            lang: Language code.
            articles: Articles to insert into the new shard generation.

        Returns:
            ShardRef identifying the newly created shard generation.
        """
        ...

    async def get_active_shards(self, *, lang: str) -> set[tuple[int, int, int]]:
        """
        Returns the set of active (shard_id, shard_gen, shard_size) for the given language.

        Args:
            lang: Language code.

        Returns:
            A set of (shard_id, shard_gen, shard_size).
        """
        ...

    async def get_shards_all_gens(self, *, lang: str, shard_id: int) -> list[ShardRow]:
        """
        Returns all generations for (lang, shard_id).

        Args:
            lang: Language code.
            shard_id: Shard id.

        Returns:
            A list of all shard generations for this shard_id.
        """
        ...

    async def delete_shard(self, *, lang: str, shard_id: int, shard_gen: int) -> None:
        """
        Deletes a shard generation and all dependent rows.

        Args:
            lang: Language code.
            shard_id: Shard id.
            shard_gen: Shard generation.

        Returns:
            None.
        """
        ...


class QuarantineRepo(Protocol):
    async def filter_not_quarantined(
        self, *, lang: str, pageids: Sequence[int]
    ) -> set[int]:
        """
        Returns the subset of pageids that are NOT present in quarantine for the given lang.

        Args:
            lang: Language code.
            pageids: Candidate pageids to check.

        Returns:
            A set of pageids that are not quarantined.
        """
        ...

    async def add_shard_to_quarantine(
        self,
        *,
        lang: str,
        shard_id: int,
        shard_gen: int,
        min_gen_waiting: int,
        max_gen_waiting: int,
    ) -> int:
        """
        Adds all articles of the given shard generation into quarantine.

        Args:
            lang: Language code.
            shard_id: Shard id.
            shard_gen: Shard generation being quarantined.
            min_gen_waiting: Inclusive lower bound for randrange().
            max_gen_waiting: Exclusive upper bound for randrange().

        Returns:
            Number of inserted/updated quarantine rows.
        """
        ...

    async def release_article(self, *, lang: str, pageid: int) -> bool:
        """
        Releases a single article from quarantine by (lang, pageid).

        Args:
            lang: Language code.
            pageid: Wikipedia page id.

        Returns:
            True if a row was deleted, False otherwise.
        """
        ...

    async def release_by_time(self, *, deadline: datetime) -> int:
        """
        Releases quarantine entries inserted not later than the given deadline.

        Args:
            deadline: All rows with inserted_at <= deadline will be deleted.

        Returns:
            Number of deleted rows.
        """
        ...

    async def release_by_shard_gen(
        self, *, lang: str, shard_id: int, shard_gen: int
    ) -> int:
        """
        Releases quarantine entries for (lang, shard_id) based on current shard generation.

        Rule:
            Delete rows where awaited_shard_gen <= shard_gen.

        Args:
            lang: Language code.
            shard_id: Shard id.
            shard_gen: Current (active) shard generation.

        Returns:
            Number of deleted rows.
        """
        ...


class Uow(Protocol):
    pool: PoolRepo
    quarantine: QuarantineRepo

    async def __aenter__(self) -> "Uow": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
