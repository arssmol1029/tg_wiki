from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ArticleUpsert:
    """
    Represents the external article identity and payload to be stored.

    Notes:
        This DTO is intended for upsert operations keyed by (lang, pageid).
    """

    lang: str
    pageid: int
    title: str
    url: str
    thumbnail_url: str | None = None
    extract: str | None = None
    extract_len: int | None = None


@dataclass(frozen=True, slots=True)
class SlotAddress:
    """
    Identifies a pool slot within a specific shard generation.
    """

    lang: str
    shard_id: int
    shard_gen: int
    shift: int


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
class ShardState:
    """
    Represents the current active generation and configuration of a shard.
    """

    lang: str
    shard_id: int
    shard_size: int
    active_gen: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Slot:
    """
    Represents an article placement into a pool slot.
    """

    shift: int
    article_id: int


class ArticleRepo(Protocol):
    """
    Provides access to stored articles and their embeddings.
    """

    async def upsert_article(
        self,
        *,
        a: ArticleUpsert,
        shard: SlotAddress,
    ) -> int:
        """
        Upserts an article by (lang, pageid) and assigns it to a pool slot address.

        Args:
            a: The article payload keyed by (lang, pageid).
            shard: The pool slot address to assign the article to.

        Returns:
            The internal article_id.
        """
        ...

    async def upsert_embedding(
        self,
        *,
        article_id: int,
        embedding: list[float],
    ) -> None:
        """
        Upserts an embedding vector for an existing article_id.
        """
        ...

    async def get_article_id(self, *, lang: str, pageid: int) -> int | None:
        """
        Returns the internal article_id for (lang, pageid) if present.
        """
        ...

    async def get_article_by_slot(self, *, slot: SlotAddress) -> ArticleRow | None:
        """
        Returns the article assigned to the given pool slot address.
        """
        ...

    async def delete_articles_by_shard_gen(
        self,
        *,
        lang: str,
        shard_id: int,
        max_shard_gen_inclusive: int,
    ) -> int:
        """
        Deletes all articles for the given shard up to (and including) shard_gen.

        Returns:
            Number of deleted articles.
        """
        ...


class ShardRepo(Protocol):
    """
    Manages active shard generation state used by the pool.
    """

    async def get_state(self, *, lang: str, shard_id: int) -> ShardState | None:
        """
        Returns shard state if it exists.
        """
        ...

    async def lock_state(self, *, lang: str, shard_id: int) -> ShardState:
        """
        Locks the shard state row for update and returns it.

        Notes:
            This method must be used to ensure only one swap happens per shard at a time.
        """
        ...

    async def set_active_gen(
        self,
        *,
        lang: str,
        shard_id: int,
        new_active_gen: int,
        shard_size: int | None = None,
    ) -> None:
        """
        Sets the active generation for a shard, creating the state row if needed.

        Args:
            shard_size: Optional. If provided, updates the shard size as well.
        """
        ...


class QuarantineRepo(Protocol):
    """
    Stores quarantine entries keyed by (lang, pageid) without foreign keys.

    Notes:
        Quarantine entries may outlive articles and shards.
    """

    async def filter_not_quarantined(
        self,
        *,
        lang: str,
        pageids: Sequence[int],
    ) -> set[int]:
        """
        Returns the subset of pageids that are NOT present in quarantine for the given lang.

        Args:
            lang: struage code.
            pageids: Candidate pageids to check.

        Returns:
            A set of pageids that are not quarantined.
        """
        ...

    async def add(
        self,
        *,
        lang: str,
        pageid: int,
        shard_id: int,
        shard_gen: int,
    ) -> None:
        """
        Adds (lang, pageid) to quarantine, recording the shard generation context.
        """
        ...

    async def remove(self, *, lang: str, pageid: int) -> None:
        """
        Removes (lang, pageid) from quarantine.
        """
        ...

    async def cleanup_by_time(
        self, *, older_than: datetime, limit: int = 50_000
    ) -> int:
        """
        Deletes quarantine entries older than the given timestamp.

        Returns:
            Number of deleted entries.
        """
        ...

    async def cleanup_by_shard_generations(
        self,
        *,
        lag_generations: int,
        limit: int = 200_000,
    ) -> int:
        """
        Deletes quarantine entries whose shard_gen is older than (active_gen - lag_generations).

        Notes:
            Only shards present in the shard state table can be compared. Entries for missing
            shards are not affected by this cleanup.

        Args:
            lag_generations: How many generations to retain in quarantine (e.g. 2 keeps
                the last two generations).
            limit: Maximum number of rows to delete in one call.

        Returns:
            Number of deleted entries.
        """
        ...


class Uow(Protocol):
    """
    Provides a transactional unit of work over a single database session/transaction.
    """

    articles: ArticleRepo
    shards: ShardRepo
    quarantine: QuarantineRepo

    async def __aenter__(self) -> "Uow": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
