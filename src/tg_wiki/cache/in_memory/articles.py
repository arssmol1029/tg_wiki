from collections import OrderedDict
from typing import Optional

from tg_wiki.domain.article import Article


class InMemoryArticleCache:
    def __init__(self, max_articles: int = 200) -> None:
        if max_articles <= 0:
            raise ValueError("max_articles must be positive")
        self._max_articles = max_articles
        self._lru: OrderedDict[int, Article] = OrderedDict()

    async def get(self, pageid: int) -> Optional[Article]:
        item = self._lru.get(pageid)
        if item is None:
            return None
        self._lru.move_to_end(pageid)
        return item

    async def update(self, article: Article) -> None:
        self._lru[article.meta.pageid] = article
        self._lru.move_to_end(article.meta.pageid)
        while len(self._lru) > self._max_articles:
            self._lru.popitem(last=False)
