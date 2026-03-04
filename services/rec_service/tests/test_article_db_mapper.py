from datetime import datetime, timezone

from rec_service.domain.article import Article
from rec_service.domain.embedding import Embedding
from rec_service.domain.vector import VECTOR_DIM
from rec_service.database.ports import ArticleRow
from rec_service.internal.article_db_mapper import from_article_row, article_to_insert


def test_from_article_row_maps_fields():
    now = datetime.now(timezone.utc)
    row = ArticleRow(
        article_id=1,
        is_active=True,
        lang="ru",
        pageid=123,
        title="T",
        url="U",
        thumbnail_url="",
        extract="",
        extract_len=0,
        created_at=now,
        updated_at=now,
    )

    a = from_article_row(row)
    assert a.pageid == 123
    assert a.title == "T"
    assert a.url == "U"
    assert a.lang == "ru"
    assert a.thumbnail_url is None
    assert a.extract is None


def test_article_to_insert_extract_len_and_embedding_cast():
    a = Article(
        pageid=1,
        title="T",
        url="U",
        lang="ru",
        thumbnail_url=None,
        extract="hello",
    )
    emb = Embedding([0.0] * VECTOR_DIM)

    ins = article_to_insert(a, embedding=emb)

    assert ins.pageid == 1
    assert ins.extract == "hello"
    assert ins.extract_len == 5
    assert isinstance(ins.embedding, list)
    assert len(ins.embedding) == VECTOR_DIM
    assert all(isinstance(x, float) for x in ins.embedding)
