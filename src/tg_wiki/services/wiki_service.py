from typing import Optional

from tg_wiki.clients.http import HttpClient, HttpNotStartedError, HttpRequestError
import tg_wiki.wiki.client as wiki


class WikiService:
    _http: HttpClient

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @property
    def http(self) -> HttpClient:
        return self._http

    @staticmethod
    def is_valid_article(
        article: dict, min_length: int = 0, max_length: int = 10000
    ) -> bool:
        """
        Filters the raw article data

        Args:
            article: The raw data of the article as returned by the Wikipedia API.

        Returns:
            True if the article is valid and contains enough information, False otherwise.
        """
        if article.get("missing") is not None:
            return False
        if not article.get("pageid"):
            return False
        if not article.get("title", "").strip():
            return False
        extract = article.get("extract", "").strip()
        if not extract:
            return False
        if len(extract) > max_length:
            return False
        if len(extract.strip()) < min_length:
            return False
        return True

    async def get_next_article(self, min_length: int = 100) -> Optional[dict]:
        """
        Fetches a random article from the Ru Wikipedia and checks if it's valid.

        Returns:
            A dictionary containing the article's information or None if no valid article was found.
        """
        try:
            data = await wiki.fetch_random(self.http)
        except (HttpRequestError, HttpNotStartedError):
            return None

        if not isinstance(data, dict):
            return None
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        article = next(iter(pages.values()))
        if not self.is_valid_article(article, min_length=min_length):
            return None

        return article

    async def get_article_by_title(self, title: str) -> Optional[dict]:
        """
        Fetches an article by its title from the Ru Wikipedia and checks if it's valid.

        Args:
            title: The title of the article to fetch.

        Returns:
            A dictionary containing the article's information, or None if no valid article was found.
        """
        try:
            data = await wiki.fetch_by_title(self.http, [title])
        except (HttpRequestError, HttpNotStartedError):
            return None

        if not isinstance(data, dict):
            return None
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        article = next(iter(pages.values()))
        if not self.is_valid_article(article):
            return None

        return article

    async def get_article_by_pageid(self, pageid: str) -> Optional[list]:
        """
        Fetches an article by its pageid from the Ru Wikipedia and checks if it's valid.

        Args:
            pageid: The pageid of the article to fetch.

        Returns:
            A dictionary containing the article's information, or None if no valid article was found.
        """
        try:
            data = await wiki.fetch_by_pageid(self.http, [pageid])
        except (HttpRequestError, HttpNotStartedError):
            return None

        if not isinstance(data, dict):
            return None
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        article = next(iter(pages.values()))
        if not self.is_valid_article(article):
            return None

        return article

    async def search_articles(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        """
        Searches for articles by query on the Ru Wikipedia.

        Args:
            query: The query to search for.

        Returns:
            A list of dictionaries containing the title and URL of the found articles.
        """
        titles: set[str] = set()

        try:
            data_title = await wiki.search_by_title(self.http, query, limit=limit)
        except (HttpRequestError, HttpNotStartedError):
            return []

        if (
            isinstance(data_title, list)
            and len(data_title) >= 2
            and isinstance(data_title[1], list)
        ):
            for title in data_title[1]:
                if not isinstance(title, str) and not title.strip():
                    continue
                titles.add(title.strip())
                if len(titles) >= limit:
                    break

        if len(titles) < limit:
            try:
                data_text = await wiki.search_by_text(
                    self.http, query, limit=limit - len(titles)
                )
            except (HttpRequestError, HttpNotStartedError):
                data_text = None

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

        try:
            pages_data = await wiki.fetch_by_title(self.http, list(titles))
        except (HttpRequestError, HttpNotStartedError):
            return []

        if not isinstance(pages_data, dict):
            return []

        pages = pages_data.get("query", {}).get("pages", {})
        if not isinstance(pages, dict) or not pages:
            return []

        out: list[dict[str, str]] = []
        for page in pages.values():
            if not page:
                continue

            if not self.is_valid_article(page):
                continue

            pageid = page.get("pageid")
            url = page.get("fullurl", "")
            title = page.get("title", "")

            if pageid and url and title:
                out.append(
                    {
                        "title": str(title),
                        "pageid": str(pageid),
                        "url": str(url),
                    }
                )

        return out
