from scpedia_protos.wiki.v1 import wiki_pb2

from wiki_service.domain.article import Article


def to_pb_article(article: Article) -> wiki_pb2.Article:
    return wiki_pb2.Article(
        pageid=article.pageid,
        title=article.title,
        lang=article.lang,
        url=article.url or "",
        thumbnail_url=article.thumbnail_url or "",
        extract=article.extract or "",
    )
