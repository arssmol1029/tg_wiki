from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class ArticleMeta:
    pageid: int
    title: str
    url: str
    thumbnail_url: Optional[str] = None

    def has_thumbnail(self) -> bool:
        return self.thumbnail_url is not None


@dataclass(frozen=True, slots=True)
class Article:
    meta: ArticleMeta
    extract: Optional[str] = None
    lang: str = "ru"


@dataclass(frozen=True, slots=True)
class ArticleEmbedding:
    pageid: int
    vector: list[float]
    model: Optional[str] = None


__all__ = ["ArticleMeta", "Article", "ArticleEmbedding"]
