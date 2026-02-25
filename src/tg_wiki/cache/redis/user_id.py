from typing import Optional


class RedisUserIDCache:
    def __init__(self, redis, *, prefix: str = "tg_wiki", ttl: int = 24 * 3600) -> None:
        self._r = redis
        self._prefix = prefix
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self._ttl = ttl

    def _key(self, provider: str, external_id: int) -> str:
        return f"{self._prefix}:settings:{provider}:{external_id}"

    async def get(self, provider: str, external_id: int) -> Optional[int]:
        key = self._key(provider, external_id)
        user_id = await self._r.get(key)
        if user_id is None:
            return None
        return int(user_id)

    async def update(self, user_id: int, provider: str, external_id: int) -> None:
        key = self._key(provider, external_id)
        await self._r.set(key, int(user_id), ex=self._ttl)
