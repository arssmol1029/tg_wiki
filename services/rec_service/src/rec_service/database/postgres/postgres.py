from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from rec_service.database.models import (
    Article,
    ArticleEmbedding,
    QuarantineArticle,
    User,
    user_seen_articles,
)
from rec_service.database.ports import (
    ArticleInsert,
    ArticleRow,
    PoolRepo,
    QuarantineRepo,
    Uow,
    UserRepo,
    zero_vec,
)


def _to_article_row(m: sa.RowMapping) -> ArticleRow:
    return ArticleRow(
        article_id=int(m["article_id"]),
        is_active=bool(m["is_active"]),
        lang=str(m["lang"]),
        pageid=int(m["pageid"]),
        title=str(m["title"]),
        url=str(m["url"]),
        thumbnail_url=str(m["thumbnail_url"]),
        extract=str(m["extract"]),
        extract_len=int(m["extract_len"]),
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


_ARTICLE_COLS = (
    Article.article_id.label("article_id"),
    Article.is_active.label("is_active"),
    Article.lang.label("lang"),
    Article.pageid.label("pageid"),
    Article.title.label("title"),
    Article.url.label("url"),
    Article.thumbnail_url.label("thumbnail_url"),
    Article.extract.label("extract"),
    Article.extract_len.label("extract_len"),
    Article.created_at.label("created_at"),
    Article.updated_at.label("updated_at"),
)


class PgUserRepo(UserRepo):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def create_user(
        self, *, user_id: int, pref: list[float] | None = None, calibration_size: int
    ) -> bool:
        """
        Add a new user to the database.

        Args:
            user_id: The unique identifier of the user to be created.
            pref: User preference vector. If None set zero vector.
            calibration_size: Size of inserted user calibration pool

        Returns:
            True if the user was successfully created or already exists, False otherwise.
        """
        if pref is None:
            pref = zero_vec()
        stmt = (
            pg_insert(User)
            .values(
                user_id=user_id,
                preference=list(pref),
                calibration_size=calibration_size,
                total_seen_articles=0,
            )
            .on_conflict_do_nothing(index_elements=[User.user_id])
        )
        await self._s.execute(stmt)
        return True

    async def get_user_pref(self, *, user_id: int) -> list[float] | None:
        """
        Retrieve user preference vector.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            User preference vector or None if user or his preference not found.
        """
        stmt = sa.select(User.preference).where(User.user_id == user_id)
        res = await self._s.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_calibration_size(self, *, user_id: int) -> int | None:
        """
        Returns:
            User calibration size or None if user not found.
        """
        stmt = sa.select(User.calibration_size).where(User.user_id == user_id)
        res = await self._s.execute(stmt)
        v = res.scalar_one_or_none()
        return None if v is None else int(v)

    async def get_user_total_seen(self, *, user_id: int) -> int | None:
        """
        Returns:
            User total seen articles field value or None if user not found.
        """
        stmt = sa.select(User.total_seen_articles).where(User.user_id == user_id)
        res = await self._s.execute(stmt)
        v = res.scalar_one_or_none()
        return None if v is None else int(v)

    async def update_user_pref(self, *, user_id: int, pref: list[float]) -> bool:
        """
        Update user preference vector.

        Args:
            user_id: The unique identifier of the user.
            pref: The preference vector to be updated.

        Returns:
            True if the user preference was successfully updated, False otherwise.
        """
        stmt = (
            sa.update(User)
            .where(User.user_id == user_id)
            .values(preference=list(pref))
            .returning(User.user_id)
        )
        res = await self._s.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def reset_user(self, *, user_id: int, calibration_size: int) -> bool:
        """
        Reset user preference.

        Args:
            user_id: The unique identifier of the user to be added.
            calibration_size: Size of inserted user calibration pool size.

        Returns:
            True if the user preference was successfully reseted, False otherwise.
        """
        values: dict[str, object] = {
            "preference": zero_vec(),
            "total_seen_articles": 0,
            "calibration_size": calibration_size,
        }

        await self._s.execute(
            sa.delete(user_seen_articles).where(user_seen_articles.c.user_id == user_id)
        )

        stmt = (
            sa.update(User)
            .where(User.user_id == user_id)
            .values(**values)
            .returning(User.user_id)
        )
        res = await self._s.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def delete_user(self, *, user_id: int) -> bool:
        """
        Delete user

        Args:
            user_id: The unique identifier of the user to be deleted.

        Returns:
            True if the user was successfully deleted or not exists, False otherwise.
        """
        stmt = sa.delete(User).where(User.user_id == user_id)
        res = await self._s.execute(stmt)
        return True

    async def get_max_user_seen(self, *, lang: str) -> list[int]:
        """
        Returns pageids of articles viewed by the most active user (with the most records in user_seen_articles)
        in descending order of the total number of views on them.

        Returns:
            List of selected pageids.
        """
        active_user_stmt = (
            sa.select(user_seen_articles.c.user_id)
            .select_from(
                user_seen_articles.join(
                    Article, Article.article_id == user_seen_articles.c.article_id
                )
            )
            .where(Article.lang == lang, Article.is_active.is_(True))
            .group_by(user_seen_articles.c.user_id)
            .order_by(sa.desc(sa.func.count()))
            .limit(1)
        )
        res = await self._s.execute(active_user_stmt)
        user_id = res.scalar_one_or_none()
        if user_id is None:
            return []

        popularity_sq = (
            sa.select(
                user_seen_articles.c.article_id.label("article_id"),
                sa.func.count().label("views"),
            )
            .group_by(user_seen_articles.c.article_id)
            .subquery()
        )

        stmt = (
            sa.select(Article.pageid)
            .select_from(
                user_seen_articles.join(
                    Article, Article.article_id == user_seen_articles.c.article_id
                ).join(popularity_sq, popularity_sq.c.article_id == Article.article_id)
            )
            .where(
                user_seen_articles.c.user_id == user_id,
                Article.lang == lang,
                Article.is_active.is_(True),
            )
            .order_by(
                sa.desc(popularity_sq.c.views),
                sa.desc(user_seen_articles.c.inserted_at),
            )
        )

        res2 = await self._s.execute(stmt)
        return [int(x) for x in res2.scalars().all()]


class PgPoolRepo(PoolRepo):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def add_articles(
        self, *, articles: Sequence[ArticleInsert], is_active: bool = True
    ) -> list[int]:
        """
        Add articles.

        Returns:
            List of inserted articles pageids
        """
        if not articles:
            return []

        rows = [
            dict(
                lang=a.lang,
                pageid=a.pageid,
                title=a.title,
                url=a.url,
                thumbnail_url=a.thumbnail_url,
                extract=a.extract,
                extract_len=a.extract_len,
                is_active=bool(is_active),
            )
            for a in articles
        ]

        ins_articles = (
            pg_insert(Article)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[Article.lang, Article.pageid])
            .returning(Article.article_id, Article.pageid)
        )
        res = await self._s.execute(ins_articles)
        inserted = res.all()
        if not inserted:
            return []

        emb_by_pageid: dict[int, list[float]] = {
            int(a.pageid): list(a.embedding) for a in articles
        }

        emb_rows = []
        for article_id, pageid in inserted:
            emb = emb_by_pageid.get(int(pageid))
            if emb is None:
                continue
            emb_rows.append(dict(article_id=int(article_id), embedding=emb))

        if emb_rows:
            ins_emb = pg_insert(ArticleEmbedding).values(emb_rows)
            ins_emb = ins_emb.on_conflict_do_update(
                index_elements=[ArticleEmbedding.article_id],
                set_={
                    "embedding": ins_emb.excluded.embedding,
                    "updated_at": sa.func.now(),
                },
            )
            await self._s.execute(ins_emb)

        return [int(pageid) for (_, pageid) in inserted]

    async def add_article(
        self, *, article: ArticleInsert, is_active: bool = True
    ) -> bool:
        """
        Add article.

        Returns:
            True if article was added, otherwise False
        """
        inserted = await self.add_articles(articles=[article], is_active=is_active)
        return bool(inserted)

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
        ids = [int(x) for x in pageids]
        if not ids:
            return []

        stmt = sa.select(*_ARTICLE_COLS).where(
            Article.lang == lang,
            Article.pageid.in_(ids),
            Article.is_active.is_(True),
        )
        res = await self._s.execute(stmt)
        return [_to_article_row(r._mapping) for r in res.all()]

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
        stmt = (
            sa.select(*_ARTICLE_COLS)
            .where(
                Article.lang == lang,
                Article.pageid == int(pageid),
                Article.is_active.is_(True),
            )
            .limit(1)
        )
        res = await self._s.execute(stmt)
        row = res.first()
        return None if row is None else _to_article_row(row._mapping)

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
        if count <= 0:
            return []

        dist = ArticleEmbedding.embedding.l2_distance(pref)

        stmt = (
            sa.select(*_ARTICLE_COLS)
            .select_from(Article)
            .join(ArticleEmbedding, ArticleEmbedding.article_id == Article.article_id)
            .where(
                Article.lang == lang,
                Article.is_active.is_(True),
                Article.extract_len >= int(min_length),
            )
            .order_by(dist.asc())
            .limit(int(count))
        )

        res = await self._s.execute(stmt)
        return [_to_article_row(r._mapping) for r in res.all()]

    async def get_active_articles_count(self, *, lang: str) -> int:
        """
        Args:
            lang: Language code.

        Returns:
            Count of active articles
        """
        stmt = (
            sa.select(sa.func.count())
            .select_from(Article)
            .where(
                Article.lang == lang,
                Article.is_active.is_(True),
            )
        )
        res = await self._s.execute(stmt)
        return int(res.scalar_one())

    async def get_inactive_articles_count(self, *, lang: str) -> int:
        """
        Args:
            lang: Language code.

        Returns:
            Count of inactive articles
        """
        stmt = (
            sa.select(sa.func.count())
            .select_from(Article)
            .where(
                Article.lang == lang,
                Article.is_active.is_(False),
            )
        )
        res = await self._s.execute(stmt)
        return int(res.scalar_one())

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
        ids = [int(x) for x in pageids]
        if not ids:
            return False

        stmt = (
            sa.update(Article)
            .where(Article.lang == lang, Article.pageid.in_(ids))
            .values(is_active=bool(is_active))
            .returning(Article.article_id)
        )
        res = await self._s.execute(stmt)
        return res.first() is not None

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
        stmt = (
            sa.select(ArticleEmbedding.embedding)
            .select_from(Article)
            .join(ArticleEmbedding, ArticleEmbedding.article_id == Article.article_id)
            .where(
                Article.lang == lang,
                Article.pageid == int(pageid),
            )
            .limit(1)
        )
        res = await self._s.execute(stmt)
        return res.scalar_one_or_none()

    async def delete_articles(self, *, lang: str, pageids: Iterable[int]) -> int:
        """
        Delete articles by (lang, pageid).

        Args:
            lang: Language code.
            pageids: Iterable object of Wikipedia page id.

        Returns:
            Count of deleted articles
        """
        ids = [int(x) for x in pageids]
        if not ids:
            return 0

        stmt = (
            sa.delete(Article)
            .where(Article.lang == lang, Article.pageid.in_(ids))
            .returning(Article.article_id)
        )
        res = await self._s.execute(stmt)
        return len(res.scalars().all())

    async def delete_article(self, *, lang: str, pageid: int) -> bool:
        """
        Delete article by (lang, pageid).

        Args:
            lang: Language code.
            pageid: Wikipedia page id.

        Returns:
            True if article was deleted, otherwhise False
        """
        stmt = (
            sa.delete(Article)
            .where(Article.lang == lang, Article.pageid == int(pageid))
            .returning(Article.article_id)
        )
        res = await self._s.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def delete_articles_by_time(self, *, lang: str, count: int) -> int:
        """
        Delete the count oldest articles.

        Args:
            lang: Language code.
            count: Count of articles to delete.

        Returns:
            Count of deleted articles
        """
        if count <= 0:
            return 0

        subq = (
            sa.select(Article.article_id)
            .where(Article.lang == lang, Article.is_active.is_(False))
            .order_by(Article.created_at.asc())
            .limit(int(count))
            .subquery()
        )
        stmt = (
            sa.delete(Article)
            .where(Article.article_id.in_(sa.select(subq.c.article_id)))
            .returning(Article.article_id)
        )
        res = await self._s.execute(stmt)
        return len(res.scalars().all())


class PgQuarantineRepo(QuarantineRepo):
    def __init__(self, session: AsyncSession):
        self._s = session

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
        ids = [int(x) for x in pageids]
        if not ids:
            return set()

        stmt = sa.select(QuarantineArticle.pageid).where(
            QuarantineArticle.lang == lang,
            QuarantineArticle.pageid.in_(ids),
        )
        res = await self._s.execute(stmt)
        quarantined = {int(x) for x in res.scalars().all()}
        return set(ids) - quarantined

    async def add_articles(self, *, lang: str, pageids: Iterable[int]) -> int:
        """
        Add articles into quarantine.

        Args:
            lang: Language code.
            pageids: List of pageids of articles.

        Returns:
            Number of inserted/updated quarantine rows.
        """
        ids = [int(x) for x in pageids]
        if not ids:
            return 0

        rows = [dict(lang=lang, pageid=pid) for pid in ids]
        stmt = (
            pg_insert(QuarantineArticle)
            .values(rows)
            .on_conflict_do_update(
                index_elements=[QuarantineArticle.lang, QuarantineArticle.pageid],
                set_={"inserted_at": sa.func.now()},
            )
            .returning(Article.article_id)
        )
        res = await self._s.execute(stmt)
        return len(res.scalars().all())

    async def release_by_time(self, *, deadline: datetime) -> int:
        """
        Release quarantine entries inserted not later than the given deadline.

        Args:
            deadline: All rows with inserted_at <= deadline will be deleted.

        Returns:
            Number of deleted rows.
        """
        stmt = (
            sa.delete(QuarantineArticle)
            .where(QuarantineArticle.inserted_at <= deadline)
            .returning(Article.article_id)
        )
        res = await self._s.execute(stmt)
        return len(res.scalars().all())


class PgUow(Uow):
    def __init__(self, sm: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sm
        self._s: AsyncSession | None = None

        self.pool: PoolRepo
        self.quarantine: QuarantineRepo

    async def __aenter__(self) -> "PgUow":
        self._s = self._sm()
        self.users = PgUserRepo(self._s)
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
