from dataclasses import dataclass

from scpedia_protos.wiki.v1 import wiki_pb2


@dataclass(frozen=True)
class ArticleMeta:
    pageid: int
    title: str
    url: str | None = None
    thumbnail_url: str | None = None


@dataclass(frozen=True)
class Article:
    meta: ArticleMeta
    extract: str | None
    lang: str


def to_pb_meta(m: ArticleMeta) -> wiki_pb2.ArticleMeta:
    return wiki_pb2.ArticleMeta(
        pageid=m.pageid,
        title=m.title,
        url=m.url or "",
        thumbnail_url=m.thumbnail_url or "",
    )


def to_pb_article(a: Article) -> wiki_pb2.Article:
    return wiki_pb2.Article(
        meta=to_pb_meta(a.meta),
        extract=a.extract or "",
        lang=a.lang,
    )
