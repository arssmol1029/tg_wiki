from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence

import sqlalchemy as sa
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pool_service.domain.embedding import EMBEDDING_DIM

from pool_service.database.ports import (
    ArticleInsert,
    ArticleRow,
    PoolRepo,
    QuarantineRepo,
    ShardRef,
    ShardRow,
    Uow,
)

from pool_service.database.models import (
    Article,
    ArticleEmbedding,
    QuarantineArticle,
    Shard,
    ShardCount,
)


def _article_row(obj: Article) -> ArticleRow:
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


def _shard_row(obj: Shard) -> ShardRow:
    return ShardRow(
        lang=str(obj.lang),
        shard_id=int(obj.shard_id),
        shard_gen=int(obj.shard_gen),
        shard_size=int(obj.shard_size),
        created_at=obj.created_at,
    )


class PgPoolRepo(PoolRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_article(self, *, lang: str, pageid: int) -> ArticleRow | None:
        query = select(Article).where(Article.lang == lang, Article.pageid == pageid)
        obj = (await self._session.execute(query)).scalar_one_or_none()
        return _article_row(obj) if obj is not None else None

    async def get_best_articles(
        self,
        *,
        lang: str,
        preference: list[float],
        count: int,
    ) -> list[ArticleRow]:
        if count <= 0:
            return []
        if len(preference) != EMBEDDING_DIM:
            raise ValueError(
                f"preference dim mismatch: expected {EMBEDDING_DIM}, got {len(preference)}"
            )

        active = (
            select(
                Shard.lang.label("lang"),
                Shard.shard_id.label("shard_id"),
                func.max(Shard.shard_gen).label("active_gen"),
            )
            .where(Shard.lang == lang)
            .group_by(Shard.lang, Shard.shard_id)
            .subquery()
        )

        dist = ArticleEmbedding.embedding.l2_distance(preference)

        query = (
            select(Article)
            .join(ArticleEmbedding, ArticleEmbedding.article_id == Article.article_id)
            .join(
                active,
                sa.and_(
                    Article.lang == active.c.lang,
                    Article.shard_id == active.c.shard_id,
                    Article.shard_gen == active.c.active_gen,
                ),
            )
            .where(Article.lang == lang)
            .order_by(dist.asc())
            .limit(count)
        )

        rows = (await self._session.execute(query)).scalars().all()
        return [_article_row(row) for row in rows]

    async def add_shard(
        self,
        *,
        lang: str,
        articles: Sequence[ArticleInsert],
    ) -> ShardRef:
        if not articles:
            raise ValueError("articles must be non-empty")

        for article in articles:
            if len(article.embedding) != EMBEDDING_DIM:
                raise ValueError(
                    f"embedding dim mismatch for pageid={article.pageid}: "
                    f"expected {EMBEDDING_DIM}, got {len(article.embedding)}"
                )

        sc_query = select(ShardCount).where(ShardCount.lang == lang).with_for_update()
        sc = (await self._session.execute(sc_query)).scalar_one_or_none()
        if sc is None:
            raise ValueError(f"ShardCount is not configured for lang={lang!r}")

        active_limit = int(sc.active_shards)
        if active_limit <= 0:
            raise ValueError(f"ShardCount.active_shards must be > 0 for lang={lang!r}")

        active_ids_query = select(Shard.shard_id).where(Shard.lang == lang).distinct()
        active_ids = [
            int(x)
            for x in (await self._session.execute(active_ids_query)).scalars().all()
        ]
        n_active = len(active_ids)

        if n_active < active_limit:
            max_id_query = select(func.max(Shard.shard_id)).where(Shard.lang == lang)
            max_id = (await self._session.execute(max_id_query)).scalar_one_or_none()
            new_shard_id = int(max_id) + 1 if max_id is not None else 0
            new_gen = 0
        else:
            rnd_query = (
                select(Shard.shard_id)
                .where(Shard.lang == lang)
                .distinct()
                .order_by(func.random())
                .limit(1)
            )
            shard_id = int((await self._session.execute(rnd_query)).scalar_one())
            active_gen_query = select(func.max(Shard.shard_gen)).where(
                Shard.lang == lang, Shard.shard_id == shard_id
            )
            active_gen = int(
                (await self._session.execute(active_gen_query)).scalar_one()
            )
            new_shard_id = shard_id
            new_gen = active_gen + 1

        shard_size = len(articles)

        await self._session.execute(
            insert(Shard).values(
                lang=lang,
                shard_id=new_shard_id,
                shard_gen=new_gen,
                shard_size=shard_size,
            )
        )

        for shift, article in enumerate(articles):
            thumb = article.thumbnail_url or ""
            extract = article.extract or ""
            extract_len = (
                article.extract_len if article.extract_len is not None else len(extract)
            )

            stmt = (
                insert(Article)
                .values(
                    lang=lang,
                    pageid=article.pageid,
                    shard_id=new_shard_id,
                    shard_gen=new_gen,
                    shift=shift,
                    title=article.title,
                    url=article.url,
                    thumbnail_url=thumb,
                    extract=extract,
                    extract_len=extract_len,
                )
                .on_conflict_do_update(
                    index_elements=[Article.lang, Article.pageid],
                    set_={
                        "shard_id": new_shard_id,
                        "shard_gen": new_gen,
                        "shift": shift,
                        "title": article.title,
                        "url": article.url,
                        "thumbnail_url": thumb,
                        "extract": extract,
                        "extract_len": extract_len,
                        "updated_at": func.now(),
                    },
                )
                .returning(Article.article_id)
            )
            article_id = int((await self._session.execute(stmt)).scalar_one())

            emb_stmt = (
                insert(ArticleEmbedding)
                .values(article_id=article_id, embedding=article.embedding)
                .on_conflict_do_update(
                    index_elements=[ArticleEmbedding.article_id],
                    set_={"embedding": article.embedding, "updated_at": func.now()},
                )
            )
            await self._session.execute(emb_stmt)

        return ShardRef(lang=lang, shard_id=new_shard_id, shard_gen=new_gen)

    async def get_active_shards(self, *, lang: str) -> set[tuple[int, int, int]]:
        query = (
            select(Shard.shard_id, func.max(Shard.shard_gen), Shard.shard_size)
            .where(Shard.lang == lang)
            .group_by(Shard.shard_id)
        )
        rows = (await self._session.execute(query)).all()
        return {
            (int(shard_id), int(active_gen), int(shard_size))
            for shard_id, active_gen, shard_size in rows
        }

    async def get_shards_all_gens(self, *, lang: str, shard_id: int) -> list[ShardRow]:
        query = (
            select(Shard)
            .where(Shard.lang == lang, Shard.shard_id == shard_id)
            .order_by(Shard.shard_gen.asc())
        )
        rows = (await self._session.execute(query)).scalars().all()
        return [_shard_row(r) for r in rows]

    async def delete_shard(self, *, lang: str, shard_id: int, shard_gen: int) -> None:
        stmt = delete(Shard).where(
            Shard.lang == lang,
            Shard.shard_id == shard_id,
            Shard.shard_gen == shard_gen,
        )
        await self._session.execute(stmt)


class PgQuarantineRepo(QuarantineRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def filter_not_quarantined(
        self, *, lang: str, pageids: Sequence[int]
    ) -> set[int]:
        if not pageids:
            return set()

        query = select(QuarantineArticle.pageid).where(
            QuarantineArticle.lang == lang,
            QuarantineArticle.pageid.in_(list(pageids)),
        )
        quarantined = set((await self._session.execute(query)).scalars().all())
        return set(pageids) - quarantined

    async def add_shard_to_quarantine(
        self,
        *,
        lang: str,
        shard_id: int,
        shard_gen: int,
        min_gen_waiting: int,
        max_gen_waiting: int,
    ) -> int:
        if min_gen_waiting < 0:
            raise ValueError("min_gen_waiting must be >= 0")
        if max_gen_waiting <= min_gen_waiting:
            raise ValueError("max_gen_waiting must be > min_gen_waiting")

        width = max_gen_waiting - min_gen_waiting

        delta = sa.cast(func.floor(func.random() * width), sa.Integer) + min_gen_waiting
        awaited = shard_gen + delta

        src = select(
            Article.lang.label("lang"),
            Article.pageid.label("pageid"),
            sa.literal(shard_id).label("shard_id"),
            awaited.label("awaited_shard_gen"),
        ).where(
            Article.lang == lang,
            Article.shard_id == shard_id,
            Article.shard_gen == shard_gen,
        )

        ins = insert(QuarantineArticle).from_select(
            ["lang", "pageid", "shard_id", "awaited_shard_gen"],
            src,
        )

        stmt = ins.on_conflict_do_update(
            index_elements=[QuarantineArticle.lang, QuarantineArticle.pageid],
            set_={
                "shard_id": ins.excluded.shard_id,
                "awaited_shard_gen": func.greatest(
                    QuarantineArticle.awaited_shard_gen,
                    ins.excluded.awaited_shard_gen,
                ),
                "inserted_at": func.now(),
            },
        )

        res = await self._session.execute(stmt)
        return int(res.rowcount or 0)  # type: ignore[attr-defined]

    async def release_article(self, *, lang: str, pageid: int) -> bool:
        stmt = delete(QuarantineArticle).where(
            QuarantineArticle.lang == lang,
            QuarantineArticle.pageid == pageid,
        )
        res = await self._session.execute(stmt)
        return bool(res.rowcount)  # type: ignore[attr-defined]

    async def release_by_time(self, *, deadline: datetime) -> int:
        stmt = delete(QuarantineArticle).where(
            QuarantineArticle.inserted_at <= deadline
        )
        res = await self._session.execute(stmt)
        return int(res.rowcount or 0)  # type: ignore[attr-defined]

    async def release_by_shard_gen(
        self, *, lang: str, shard_id: int, shard_gen: int
    ) -> int:
        stmt = delete(QuarantineArticle).where(
            QuarantineArticle.lang == lang,
            QuarantineArticle.shard_id == shard_id,
            QuarantineArticle.awaited_shard_gen <= shard_gen,
        )
        res = await self._session.execute(stmt)
        return int(res.rowcount or 0)  # type: ignore[attr-defined]


class PgUow(Uow):
    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm
        self._s: AsyncSession | None = None

        self.pool: PoolRepo
        self.quarantine: QuarantineRepo

    async def __aenter__(self) -> "PgUow":
        self._s = self._sm()
        self.pool = PgPoolRepo(self._s)
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


def make_uow_factory(sm: async_sessionmaker[AsyncSession]) -> Callable[[], PgUow]:
    return lambda: PgUow(sm)
