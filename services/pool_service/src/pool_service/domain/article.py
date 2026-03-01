from dataclasses import dataclass

from pool_service.domain.embedding import EmbeddingVector


@dataclass(frozen=True)
class Article:
    pageid: int
    title: str
    url: str
    lang: str
    thumbnail_url: str | None = None
    extract: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddedArticle:
    article: Article
    embedding: EmbeddingVector
