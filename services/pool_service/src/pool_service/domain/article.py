from dataclasses import dataclass

from scpedia_protos.pool.v1 import pool_pb2
from scpedia_protos.wiki.v1 import wiki_pb2

from pool_service.domain.embedding import EmbeddingVector


@dataclass(frozen=True)
class ArticleMeta:
    pageid: int
    title: str
    url: str
    thumbnail_url: str | None = None


@dataclass(frozen=True)
class Article:
    meta: ArticleMeta
    extract: str | None
    lang: str


@dataclass(frozen=True, slots=True)
class PooledArticle:
    article: Article
    embedding: EmbeddingVector


def from_wiki_pb_meta(m: wiki_pb2.ArticleMeta) -> ArticleMeta:
    return ArticleMeta(
        pageid=m.pageid,
        title=m.title,
        url=m.url or "",
        thumbnail_url=m.thumbnail_url or "",
    )


def from_wiki_pb_article(a: wiki_pb2.Article) -> Article:
    return Article(
        meta=from_wiki_pb_meta(a.meta),
        extract=a.extract or "",
        lang=a.lang,
    )


def to_pool_pb_meta(m: ArticleMeta) -> pool_pb2.ArticleMeta:
    return pool_pb2.ArticleMeta(
        pageid=m.pageid,
        title=m.title,
        url=m.url or "",
        thumbnail_url=m.thumbnail_url or "",
    )


def to_pool_pb_article(a: Article) -> pool_pb2.Article:
    return pool_pb2.Article(
        meta=to_pool_pb_meta(a.meta),
        extract=a.extract or "",
        lang=a.lang,
    )
