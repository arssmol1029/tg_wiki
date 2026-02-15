from collections import OrderedDict, defaultdict


class InMemoryUserCache:
    def __init__(self, max_articles_per_user: int = 20) -> None:
        if max_articles_per_user <= 0:
            raise ValueError("max_articles_per_user must be positive")
        self._max_articles_per_user = max_articles_per_user
        self._cache: dict[int, OrderedDict[int, None]] = defaultdict(OrderedDict)

    async def get(self, user_id: int) -> list[int]:
        return list(self._cache[user_id].keys())

    async def add(self, user_id: int, pageid: int) -> None:
        user_cache = self._cache[user_id]
        user_cache[pageid] = None
        user_cache.move_to_end(pageid)
        while len(user_cache) > self._max_articles_per_user:
            user_cache.popitem(last=False)
