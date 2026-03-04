import pytest

from datetime import datetime, timezone

from rec_service.pool.pool_service import PoolService
from rec_service.database.ports import ArticleRow
from rec_service.domain.vector import VECTOR_DIM


@pytest.mark.asyncio
async def test_get_best_articles_count_le_zero_is_fast_empty(
    dummy_uow_factory, dummy_pool_repo
):
    pool = dummy_pool_repo

    svc = PoolService(uow_factory=dummy_uow_factory(pool=pool))  # type: ignore

    res = await svc.get_best_articles(lang="ru", pref=[0.0] * VECTOR_DIM, count=0)

    assert res == []
    pool.get_best_articles.assert_not_called()


@pytest.mark.asyncio
async def test_get_best_articles_maps_rows_to_domain_articles(
    dummy_uow_factory, dummy_pool_repo
):
    pool = dummy_pool_repo
    now = datetime.now(timezone.utc)
    pool.get_best_articles.return_value = [
        ArticleRow(
            article_id=1,
            is_active=True,
            lang="ru",
            pageid=10,
            title="T",
            url="U",
            thumbnail_url="",
            extract="hello",
            extract_len=5,
            created_at=now,
            updated_at=now,
        )
    ]

    svc = PoolService(uow_factory=lambda: dummy_uow_factory(pool=pool))  # type: ignore

    res = await svc.get_best_articles(lang="ru", pref=[0.0] * VECTOR_DIM, count=1)
    assert len(res) == 1
    assert res[0].pageid == 10
    assert res[0].title == "T"
    assert res[0].extract == "hello"


@pytest.mark.asyncio
async def test_get_article_embedding_wraps_into_embedding_or_none(
    dummy_uow_factory, dummy_pool_repo
):
    pool = dummy_pool_repo
    pool.get_article_embedding.return_value = [0.0] * VECTOR_DIM

    svc = PoolService(uow_factory=lambda: dummy_uow_factory(pool=pool))  # type: ignore

    emb = await svc.get_article_embedding(lang="ru", pageid=1)
    assert emb is not None
    assert len(emb.data) == VECTOR_DIM

    pool.get_article_embedding.return_value = None
    emb2 = await svc.get_article_embedding(lang="ru", pageid=1)
    assert emb2 is None
