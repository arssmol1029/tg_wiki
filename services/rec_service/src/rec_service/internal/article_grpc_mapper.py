from scpedia_protos.rec.v1 import rec_pb2
from scpedia_protos.wiki.v1 import wiki_pb2

from rec_service.domain.article import Article


def to_rec_pb_article(
    article: Article, *, text: bool = True, image: bool = True
) -> rec_pb2.Article:
    return rec_pb2.Article(
        pageid=article.pageid,
        title=article.title,
        url=article.url or "",
        lang=article.lang,
        thumbnail_url=(article.thumbnail_url or "") if image else "",
        extract=(article.extract or "") if text else "",
    )


def from_wiki_pb_article(article: wiki_pb2.Article) -> Article:
    return Article(
        pageid=article.pageid,
        title=article.title,
        lang=article.lang,
        url=article.url or "",
        thumbnail_url=article.thumbnail_url or "",
        extract=article.extract or "",
    )
