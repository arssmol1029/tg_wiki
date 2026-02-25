from typing import Optional

from tg_wiki.domain.user import UserSettings
from .codec import dumps_settings, loads_settings


class RedisUserSettingsCache:
    def __init__(self, redis, *, prefix: str = "tg_wiki", ttl: int = 24 * 3600) -> None:
        self._r = redis
        self._prefix = prefix
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self._ttl = ttl

    def _key(self, user_id: int) -> str:
        return f"{self._prefix}:settings:{user_id}"

    async def get(self, user_id: int) -> Optional[UserSettings]:
        key = self._key(user_id)
        raw = await self._r.get(key)
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return loads_settings(raw)

    async def update(self, user_id: int, settings: UserSettings) -> None:
        key = self._key(user_id)
        val = dumps_settings(settings)
        await self._r.set(key, val, ex=self._ttl)
