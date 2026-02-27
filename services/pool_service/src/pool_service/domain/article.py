from dataclasses import dataclass


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
