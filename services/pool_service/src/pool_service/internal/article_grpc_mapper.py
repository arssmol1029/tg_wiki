from scpedia_protos.pool.v1 import pool_pb2
from scpedia_protos.wiki.v1 import wiki_pb2

from pool_service.domain.article import Article


def from_wiki_pb_article(article: wiki_pb2.Article) -> Article:
    return Article(
        pageid=article.pageid,
        title=article.title,
        url=article.url or "",
        lang=article.lang,
        thumbnail_url=article.thumbnail_url or "",
        extract=article.extract or "",
    )


def to_pool_pb_article(article: Article) -> pool_pb2.Article:
    return pool_pb2.Article(
        pageid=article.pageid,
        title=article.title,
        url=article.url or "",
        lang=article.lang,
        thumbnail_url=article.thumbnail_url or "",
        extract=article.extract or "",
    )
