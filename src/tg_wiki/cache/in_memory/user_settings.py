from collections import OrderedDict
from typing import Optional

from tg_wiki.domain.user import UserSettings


class InMemoryUserSettingsCache:
    def __init__(self, max_users: int = 1000) -> None:
        if max_users <= 0:
            raise ValueError("max_articles must be positive")
        self._max_users = max_users
        self._lru: OrderedDict[int, UserSettings] = OrderedDict()

    async def get(self, user_id: int) -> Optional[UserSettings]:
        item = self._lru.get(user_id)
        if item is None:
            return None
        self._lru.move_to_end(user_id)
        return item

    async def update(self, user_id, settings: UserSettings) -> None:
        self._lru[user_id] = settings
        self._lru.move_to_end(user_id)
        while len(self._lru) > self._max_users:
            self._lru.popitem(last=False)
