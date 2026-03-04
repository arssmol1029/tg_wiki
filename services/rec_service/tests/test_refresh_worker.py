import asyncio
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aio_pika")
pytest.importorskip("grpc")
pytest.importorskip("scpedia_protos.wiki.v1.wiki_pb2")

from rec_service.pool.refresh_worker import RefreshWorker, RefreshWorkerConfig
from rec_service.domain.article import Article
from rec_service.domain.embedding import Embedding
from rec_service.domain.vector import VECTOR_DIM


class DummyWiki:
    def __init__(self, seq):
        self._seq = list(seq)
        self._lock = asyncio.Lock()

    async def get_random_article(self, **kwargs):
        async with self._lock:
            if not self._seq:
                return None
            return self._seq.pop(0)


class DummyModel:
    def __init__(self, mapping):
        self._mapping = dict(mapping)

    def get_embedding(self, article: Article):
        val = self._mapping.get(article.pageid)
        if isinstance(val, Exception):
            raise val
        return val


@pytest.mark.asyncio
async def test_fetch_candidates_filters_none_and_duplicates(dummy_uow_factory):
    a1 = Article(pageid=1, title="A", url="U", lang="ru", extract="x")
    a2 = Article(pageid=2, title="B", url="U", lang="ru", extract="x")

    wiki = DummyWiki([a1, None, a1, a2])
    model = DummyModel({})

    worker = RefreshWorker(
        wiki=wiki,  # type: ignore
        model=model,  # type: ignore
        uow_factory=lambda: dummy_uow_factory(),  # type: ignore
        langs_map={"ru": 1},
        cfg=RefreshWorkerConfig(wiki_concurrency=10, embed_concurrency=10),
    )

    seen = set()
    res = await worker._fetch_candidates(lang="ru", count=4, seen_pageids=seen)

    assert [a.pageid for a in res] == [1, 2]
    assert seen == {1, 2}


@pytest.mark.asyncio
async def test_embed_many_handles_sync_and_exception(dummy_uow_factory):
    a1 = Article(pageid=1, title="A", url="U", lang="ru", extract="x")
    a2 = Article(pageid=2, title="B", url="U", lang="ru", extract="x")

    emb1 = Embedding([1.0] + [0.0] * (VECTOR_DIM - 1))

    model = DummyModel({1: emb1, 2: RuntimeError("boom")})
    wiki = DummyWiki([])

    worker = RefreshWorker(
        wiki=wiki,  # type: ignore
        model=model,  # type: ignore
        uow_factory=lambda: dummy_uow_factory(),  # type: ignore
        langs_map={"ru": 1},
        cfg=RefreshWorkerConfig(
            embed_timeout_s=1.0, wiki_concurrency=10, embed_concurrency=10
        ),
    )

    pairs = await worker._embed_many(lang="ru", articles=[a1, a2])

    assert len(pairs) == 1
    assert pairs[0][0].pageid == 1
    assert isinstance(pairs[0][1], Embedding)
