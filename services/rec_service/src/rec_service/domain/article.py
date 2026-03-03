from dataclasses import dataclass

from rec_service.domain.embedding import Embedding


@dataclass(frozen=True)
class Article:
    pageid: int
    title: str
    url: str
    lang: str
    thumbnail_url: str | None = None
    extract: str | None = None
