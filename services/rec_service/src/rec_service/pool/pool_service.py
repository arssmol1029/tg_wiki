from typing import Callable

from rec_service.database.ports import Uow
from rec_service.domain.article import Article
from rec_service.domain.embedding import Embedding
from rec_service.internal.article_db_mapper import from_article_row


class PoolService:
    def __init__(self, *, uow_factory: Callable[[], Uow]):
        self._uow_factory = uow_factory

    async def get_best_articles(
        self, *, lang: str, pref: list[float], count: int, min_length: int = 0
    ) -> list[Article]:
        """
        Returns top-count best matching articles by the preference vector.

        Args:
            pref: User preference vector
            count: Number of articles to return.
            lang: Language code.

        Returns:
            List of articles.
        """
        if count <= 0:
            return []

        collected: list[Article] = []

        async with self._uow_factory() as uow:
            articles = await uow.pool.get_best_articles(
                lang=lang, pref=pref, count=count, min_length=min_length
            )

        collected = [from_article_row(article) for article in articles]

        return collected

    async def get_article_embedding(
        self, *, lang: str, pageid: int
    ) -> Embedding | None:
        """
        Return article embedding.

        Args:
            lang: Language code.
            pageid: Wikipedia page id.

        Returns:
            Article embedding or None if not found.
        """
        async with self._uow_factory() as uow:
            embedding = await uow.pool.get_article_embedding(lang=lang, pageid=pageid)
        if embedding is not None:
            return Embedding(embedding)
        return None
