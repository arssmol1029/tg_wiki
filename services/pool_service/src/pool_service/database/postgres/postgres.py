from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence

import sqlalchemy as sa
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pool_service.database.ports import (
    ArticleRepo,
    ArticleRow,
    ArticleUpsert,
    QuarantineRepo,
    ShardRepo,
    ShardState,
    SlotAddress,
    Uow,
)
from pool_service.domain.embedding import EMBEDDING_DIM

from pool_service.database.models import (
    Article,
    ArticleEmbedding,
    QuarantineArticle,
    Shard,
)


class PgArticleRepo(ArticleRepo):
    def __init__(self, s: AsyncSession) -> None:
        self._s = s

    async def upsert_article(self, *, a: ArticleUpsert, shard: SlotAddress) -> int:
        thumb = a.thumbnail_url or ""
        extract = a.extract or ""
        extract_len = a.extract_len if a.extract_len is not None else len(extract)

        stmt = (
            insert(Article)
            .values(
                lang=a.lang,
                pageid=a.pageid,
                shard_id=shard.shard_id,
                shard_gen=shard.shard_gen,
                shift=shard.shift,
                title=a.title,
                url=a.url,
                thumbnail_url=thumb,
                extract=extract,
                extract_len=extract_len,
            )
            .on_conflict_do_update(
                index_elements=[Article.lang, Article.pageid],  # UNIQUE(lang,pageid)
                set_={
                    "shard_id": shard.shard_id,
                    "shard_gen": shard.shard_gen,
                    "shift": shard.shift,
                    "title": a.title,
                    "url": a.url,
                    "thumbnail_url": thumb,
                    "extract": extract,
                    "extract_len": extract_len,
                    "updated_at": func.now(),
                },
            )
            .returning(Article.article_id)
        )
        article_id = int((await self._s.execute(stmt)).scalar_one())
        return article_id

    async def upsert_embedding(
        self, *, article_id: int, embedding: list[float]
    ) -> None:
        if len(embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"embedding dim mismatch: expected {EMBEDDING_DIM}, got {len(embedding)}"
            )

        stmt = (
            insert(ArticleEmbedding)
            .values(article_id=article_id, embedding=embedding)
            .on_conflict_do_update(
                index_elements=[ArticleEmbedding.article_id],
                set_={"embedding": embedding, "updated_at": func.now()},
            )
        )
        await self._s.execute(stmt)

    async def get_article_id(self, *, lang: str, pageid: int) -> int | None:
        q = select(Article.article_id).where(
            Article.lang == lang, Article.pageid == pageid
        )
        v = (await self._s.execute(q)).scalar_one_or_none()
        return int(v) if v is not None else None

    async def get_article_by_slot(self, *, slot: SlotAddress) -> ArticleRow | None:
        q = select(Article).where(
            Article.lang == slot.lang,
            Article.shard_id == slot.shard_id,
            Article.shard_gen == slot.shard_gen,
            Article.shift == slot.shift,
        )
        obj = (await self._s.execute(q)).scalar_one_or_none()
        if obj is None:
            return None

        return ArticleRow(
            article_id=int(obj.article_id),
            lang=str(obj.lang),
            pageid=int(obj.pageid),
            shard_id=int(obj.shard_id),
            shard_gen=int(obj.shard_gen),
            shift=int(obj.shift),
            title=str(obj.title),
            url=str(obj.url),
            thumbnail_url=str(obj.thumbnail_url),
            extract=str(obj.extract),
            extract_len=int(obj.extract_len),
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    async def delete_articles_by_shard_gen(
        self,
        *,
        lang: str,
        shard_id: int,
        max_shard_gen_inclusive: int,
    ) -> int:
        stmt = delete(Article).where(
            Article.lang == lang,
            Article.shard_id == shard_id,
            Article.shard_gen <= max_shard_gen_inclusive,
        )
        res = await self._s.execute(stmt)
        return int(res.rowcount or 0)  # type: ignore[attr-defined]


class PgShardRepo(ShardRepo):
    def __init__(self, s: AsyncSession) -> None:
        self._s = s

    async def get_state(self, *, lang: str, shard_id: int) -> ShardState | None:
        q = (
            select(Shard)
            .where(Shard.lang == lang, Shard.shard_id == shard_id)
            .order_by(Shard.shard_gen.desc())
            .limit(1)
        )
        obj = (await self._s.execute(q)).scalar_one_or_none()
        if obj is None:
            return None

        return ShardState(
            lang=str(obj.lang),
            shard_id=int(obj.shard_id),
            shard_size=int(obj.shard_size),
            active_gen=int(obj.shard_gen),
            updated_at=obj.created_at,
        )

    async def lock_state(self, *, lang: str, shard_id: int) -> ShardState:
        q = (
            select(Shard)
            .where(Shard.lang == lang, Shard.shard_id == shard_id)
            .order_by(Shard.shard_gen.desc())
            .limit(1)
            .with_for_update()
        )
        obj = (await self._s.execute(q)).scalar_one()
        return ShardState(
            lang=str(obj.lang),
            shard_id=int(obj.shard_id),
            shard_size=int(obj.shard_size),
            active_gen=int(obj.shard_gen),
            updated_at=obj.created_at,
        )

    async def set_active_gen(
        self,
        *,
        lang: str,
        shard_id: int,
        new_active_gen: int,
        shard_size: int | None = None,
    ) -> None:
        if shard_size is None:
            state = await self.get_state(lang=lang, shard_id=shard_id)
            if state is None:
                raise ValueError(
                    "shard_size must be provided when creating a new shard"
                )
            shard_size = state.shard_size

        stmt = (
            insert(Shard)
            .values(
                lang=lang,
                shard_id=shard_id,
                shard_gen=new_active_gen,
                shard_size=shard_size,
            )
            .on_conflict_do_update(
                index_elements=[Shard.lang, Shard.shard_id, Shard.shard_gen],
                set_={"shard_size": shard_size},
            )
        )
        await self._s.execute(stmt)


class PgQuarantineRepo(QuarantineRepo):
    def __init__(self, s: AsyncSession) -> None:
        self._s = s

    async def filter_not_quarantined(
        self, *, lang: str, pageids: Sequence[int]
    ) -> set[int]:
        if not pageids:
            return set()

        q = select(QuarantineArticle.pageid).where(
            QuarantineArticle.lang == lang,
            QuarantineArticle.pageid.in_(list(pageids)),
        )
        quarantined = set((await self._s.execute(q)).scalars().all())
        return set(pageids) - quarantined

    async def add(
        self, *, lang: str, pageid: int, shard_id: int, shard_gen: int
    ) -> None:
        stmt = (
            insert(QuarantineArticle)
            .values(lang=lang, pageid=pageid, shard_id=shard_id, shard_gen=shard_gen)
            .on_conflict_do_update(
                index_elements=[QuarantineArticle.lang, QuarantineArticle.pageid],
                set_={
                    "shard_id": shard_id,
                    "shard_gen": shard_gen,
                    "inserted_at": func.now(),
                },
            )
        )
        await self._s.execute(stmt)

    async def remove(self, *, lang: str, pageid: int) -> None:
        stmt = delete(QuarantineArticle).where(
            QuarantineArticle.lang == lang, QuarantineArticle.pageid == pageid
        )
        await self._s.execute(stmt)

    async def cleanup_by_time(
        self, *, older_than: datetime, limit: int = 50_000
    ) -> int:
        subq = (
            select(QuarantineArticle.lang, QuarantineArticle.pageid)
            .where(QuarantineArticle.inserted_at < older_than)
            .limit(limit)
            .subquery()
        )
        stmt = delete(QuarantineArticle).where(
            sa.tuple_(QuarantineArticle.lang, QuarantineArticle.pageid).in_(
                select(subq.c.lang, subq.c.pageid)
            )
        )
        res = await self._s.execute(stmt)
        return int(res.rowcount or 0)  # type: ignore[attr-defined]

    async def cleanup_by_shard_generations(
        self, *, lag_generations: int, limit: int = 200_000
    ) -> int:
        if lag_generations < 0:
            raise ValueError("lag_generations must be >= 0")

        active = (
            select(
                Shard.lang.label("lang"),
                Shard.shard_id.label("shard_id"),
                func.max(Shard.shard_gen).label("active_gen"),
            )
            .group_by(Shard.lang, Shard.shard_id)
            .subquery()
        )

        candidates = (
            select(QuarantineArticle.lang, QuarantineArticle.pageid)
            .select_from(QuarantineArticle)
            .join(
                active,
                sa.and_(
                    QuarantineArticle.lang == active.c.lang,
                    QuarantineArticle.shard_id == active.c.shard_id,
                ),
            )
            .where(
                QuarantineArticle.shard_gen <= (active.c.active_gen - lag_generations)
            )
            .limit(limit)
            .subquery()
        )

        stmt = delete(QuarantineArticle).where(
            sa.tuple_(QuarantineArticle.lang, QuarantineArticle.pageid).in_(
                select(candidates.c.lang, candidates.c.pageid)
            )
        )
        res = await self._s.execute(stmt)
        return int(res.rowcount or 0)  # type: ignore[attr-defined]


class PgUow(Uow):
    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm
        self._s: AsyncSession | None = None

        self.articles: ArticleRepo
        self.shards: ShardRepo
        self.quarantine: QuarantineRepo

    async def __aenter__(self) -> "PgUow":
        self._s = self._sm()
        self.articles = PgArticleRepo(self._s)
        self.shards = PgShardRepo(self._s)
        self.quarantine = PgQuarantineRepo(self._s)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self._s is not None
        try:
            if exc is None:
                await self._s.commit()
            else:
                await self._s.rollback()
        finally:
            await self._s.close()
            self._s = None


def make_uow_factory(
    sm: async_sessionmaker[AsyncSession],
) -> Callable[[], PgUow]:
    return lambda: PgUow(sm)
