import pytest

pytest.importorskip("scpedia_protos.rec.v1.rec_pb2")
pytest.importorskip("scpedia_protos.wiki.v1.wiki_pb2")

from scpedia_protos.rec.v1 import rec_pb2
from scpedia_protos.wiki.v1 import wiki_pb2

from rec_service.domain.article import Article
from rec_service.internal.article_grpc_mapper import to_rec_pb_article, from_wiki_pb_article


def test_to_rec_pb_article_respects_flags():
    a = Article(
        pageid=1,
        title="T",
        url="U",
        lang="ru",
        thumbnail_url="IMG",
        extract="hello",
    )

    pb = to_rec_pb_article(a, text=False, image=False)
    assert pb.pageid == 1
    assert pb.title == "T"
    assert pb.lang == "ru"
    assert pb.extract == ""
    assert pb.thumbnail_url == ""


def test_from_wiki_pb_article_maps_fields():
    pb = wiki_pb2.Article(pageid=1, title="T", url="U", lang="ru", thumbnail_url="", extract="")
    a = from_wiki_pb_article(pb)

    assert a.pageid == 1
    assert a.title == "T"
    assert a.url == "U"
    assert a.lang == "ru"
