from scpedia_protos.pool.v1 import pool_pb2

from pool_service.domain.article import ArticleMeta, Article


def from_pb_meta(m: pool_pb2.ArticleMeta) -> ArticleMeta:
    return ArticleMeta(
        pageid=m.pageid,
        title=m.title,
        url=m.url or "",
        thumbnail_url=m.thumbnail_url or "",
    )


def from_pb_article(a: pool_pb2.Article) -> Article:
    return Article(
        meta=from_pb_meta(a.meta),
        extract=a.extract or "",
        lang=a.lang,
    )
