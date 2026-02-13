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

    async def get_article_by_pageid(self, pageid: str) -> Optional[dict]:
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
        try:
            data = await wiki.search_by_title(self.http, query, limit=limit)
        except (HttpRequestError, HttpNotStartedError):
            return []

        if not data or not isinstance(data, list) or len(data) < 2:
            return []
        titles = data[1]

        try:
            data_title = await wiki.fetch_by_title(self.http, titles)
        except (HttpRequestError, HttpNotStartedError):
            return []

        if not isinstance(data_title, dict):
            return []
        pages_title = data_title.get("query", {}).get("pages", {})
        if not pages_title:
            return []

        results: set[dict[str, str]] = set()
        for page in pages_title.values():
            if self.is_valid_article(page):
                results.add(
                    {
                        "title": page.get("title", ""),
                        "pageid": str(page.get("pageid", "")),
                        "url": page.get("fullurl", ""),
                    }
                )

        if len(results) >= limit:
            return list(results)

        try:
            data_text = await wiki.search_by_text(
                self.http, query, limit=limit - len(results)
            )
        except (HttpRequestError, HttpNotStartedError):
            return list(results)

        if not isinstance(data_text, dict):
            return list(results)
        pages_text = data_text.get("query", {}).get("pages", {})
        if not pages_text:
            return list(results)

        for page in pages_text.values():
            if self.is_valid_article(page):
                results.add(
                    {
                        "title": page.get("title", ""),
                        "pageid": str(page.get("pageid", "")),
                        "url": page.get("fullurl", ""),
                    }
                )
        return list(results)
