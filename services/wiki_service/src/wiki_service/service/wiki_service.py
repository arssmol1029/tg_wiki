from typing import Optional
from dataclasses import dataclass

from wiki_service.service.http import HttpClient, HttpRequestError
from wiki_service.internal.map_api_lang import UnsupportedLanguage
import wiki_service.service.wiki_client as wiki


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


def _to_article_meta(raw: dict) -> ArticleMeta:
    """
    Converts the raw article data from the Wikipedia API into an ArticleMeta object.

    Args:
        raw: The raw data of the article as returned by the Wikipedia API.

    Returns:
        An ArticleMeta object containing the article's metadata.
    """
    pageid = int(raw["pageid"])
    title = str(raw.get("title", "")).strip()
    fullurl = str(raw.get("fullurl", "")).strip()

    thumb = raw.get("thumbnail")
    thumbnail_url = None
    if isinstance(thumb, dict):
        thumbnail_url = thumb.get("source")

    return ArticleMeta(
        pageid=int(pageid),
        title=title,
        url=fullurl,
        thumbnail_url=thumbnail_url,
    )


def _to_article(raw: dict, lang: str = "ru") -> Article:
    """
    Converts the raw article data from the Wikipedia API into an Article object.

    Args:
        raw: The raw data of the article as returned by the Wikipedia API.

    Returns:
        An Article object containing the article's information.
    """
    meta = _to_article_meta(raw)
    extract = str(raw.get("extract", "")).strip()

    return Article(meta=meta, extract=extract, lang=lang)


def _is_valid_article(
    article: dict, min_length: int = 0, *, text_required: bool = True
) -> bool:
    """
    Filters the raw article data

    Args:
        article: The raw data of the article as returned by the Wikipedia API.

    Returns:
        True if the article is valid and contains enough information, False otherwise.
    """
    if not isinstance(article, dict) or not article:
        return False
    if article.get("missing") is not None:
        return False
    if not article.get("pageid"):
        return False
    if not str(article.get("title", "")).strip():
        return False
    if not str(article.get("fullurl", "")).strip():
        return False
    if text_required:
        extract = str(article.get("extract", "")).strip()
        if len(extract) < min_length:
            return False
    return True


class WikiService:
    _http: HttpClient

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @property
    def http(self) -> HttpClient:
        return self._http

    async def get_random_article(
        self,
        min_length: int = 0,
        *,
        lang: str = "ru",
        text: bool = True,
        image: bool = True
    ) -> Optional[Article]:
        """
        Fetches a random article from the Ru Wikipedia and checks if it's valid.

        Returns:
            A dictionary containing the article's information or None if no valid article was found.
        """
        data = await wiki.fetch_random(self.http, lang=lang, text=text, image=image)

        if not isinstance(data, dict):
            return None
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        article = next(iter(pages.values()))
        if not _is_valid_article(article, min_length=min_length, text_required=text):
            return None

        return _to_article(article, lang=lang)

    async def get_article_by_title(
        self, title: str, *, lang: str = "ru", text: bool = True, image: bool = True
    ) -> Optional[Article]:
        """
        Fetches an article by its title from the Ru Wikipedia and checks if it's valid.

        Args:
            title: The title of the article to fetch.

        Returns:
            A dictionary containing the article's information, or None if no valid article was found.
        """
        data = await wiki.fetch_by_title(self.http, [title], text=text, image=image)

        if not isinstance(data, dict):
            return None
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        article = next(iter(pages.values()))
        if not _is_valid_article(article, text_required=text):
            return None

        return _to_article(article, lang=lang)

    async def get_article_by_pageid(
        self, pageid: int, *, lang: str = "ru", text: bool = True, image: bool = True
    ) -> Optional[Article]:
        """
        Fetches an article by its pageid from the Ru Wikipedia and checks if it's valid.

        Args:
            pageid: The pageid of the article to fetch.

        Returns:
            A dictionary containing the article's information, or None if no valid article was found.
        """
        data = await wiki.fetch_by_pageid(
            self.http, [str(pageid)], lang=lang, text=text, image=image
        )

        if not isinstance(data, dict):
            return None
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        article = next(iter(pages.values()))
        if not _is_valid_article(article, text_required=text):
            return None

        return _to_article(article, lang=lang)

    async def search_articles(
        self, query: str, *, lang: str = "ru", limit: int = 5
    ) -> list[ArticleMeta]:
        """
        Searches for articles by query on the Ru Wikipedia.

        Args:
            query: The query to search for.

        Returns:
            A list of dictionaries containing the title and URL of the found articles.
        """
        titles: set[str] = set()

        data_title = await wiki.search_by_title(
            self.http, query, lang=lang, limit=limit
        )

        if (
            isinstance(data_title, list)
            and len(data_title) >= 2
            and isinstance(data_title[1], list)
        ):
            for title in data_title[1]:
                if (not isinstance(title, str)) or (not title.strip()):
                    continue
                titles.add(title.strip())
                if len(titles) >= limit:
                    break

        if len(titles) < limit:
            data_text = await wiki.search_by_text(
                self.http, query, lang=lang, limit=limit - len(titles)
            )

            if isinstance(data_text, dict):
                search_items = data_text.get("query", {}).get("search", [])
                if isinstance(search_items, list):
                    for item in search_items:
                        if len(titles) >= limit:
                            break
                        if not isinstance(item, dict):
                            continue
                        title = str(item.get("title", "")).strip()
                        if title.strip():
                            titles.add(title)

        if not titles:
            return []

        pages_data = await wiki.fetch_by_title(
            self.http, list(titles), lang=lang, text=False
        )

        if not isinstance(pages_data, dict):
            return []

        pages = pages_data.get("query", {}).get("pages", {})
        if not isinstance(pages, dict) or not pages:
            return []

        out: list[ArticleMeta] = [
            _to_article_meta(page)
            for page in pages.values()
            if _is_valid_article(page, text_required=False)
        ]

        return out
