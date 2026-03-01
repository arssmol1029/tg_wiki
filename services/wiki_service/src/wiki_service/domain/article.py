from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    pageid: int
    title: str
    lang: str
    url: str | None = None
    thumbnail_url: str | None = None
    extract: str | None = None
