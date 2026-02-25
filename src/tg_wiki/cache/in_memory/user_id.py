from collections import OrderedDict
from typing import Optional


class InMemoryUserIDCache:
    def __init__(self, max_users: int = 1000) -> None:
        if max_users <= 0:
            raise ValueError("max_articles must be positive")
        self._max_users = max_users
        self._lru: OrderedDict[tuple[str, int], int] = OrderedDict()

    async def get(self, provider: str, external_id: int) -> Optional[int]:
        ident = (provider, external_id)

        item = self._lru.get(ident)
        if item is None:
            return None
        self._lru.move_to_end(ident)
        return item

    async def update(self, user_id, provider: str, external_id: int) -> None:
        ident = (provider, external_id)

        self._lru[ident] = user_id
        self._lru.move_to_end(ident)
        while len(self._lru) > self._max_users:
            self._lru.popitem(last=False)
