class RedisLastViewCache:
    def __init__(
        self,
        redis,
        *,
        prefix: str = "tg_wiki",
        max_articles_per_user: int = 20,
        ttl: int = 7 * 24 * 3600,
    ) -> None:
        self._r = redis
        self._prefix = prefix
        if max_articles_per_user <= 0:
            raise ValueError("max_articles_per_user must be positive")
        self._max = max_articles_per_user
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self._ttl = ttl

    def _key(self, user_id: int) -> str:
        return f"{self._prefix}:user:{int(user_id)}:recent"

    async def get(self, user_id: int) -> list[int]:
        key = self._key(user_id)
        items = await self._r.lrange(key, 0, -1)
        out: list[int] = []
        for x in items:
            if isinstance(x, (bytes, bytearray)):
                x = x.decode("utf-8")
            try:
                out.append(int(x))
            except ValueError:
                continue
        return out

    async def update(self, user_id: int, pageid: int) -> None:
        key = self._key(user_id)

        pipe = self._r.pipeline(transaction=True)
        pipe.lrem(key, 0, int(pageid))
        pipe.lpush(key, int(pageid))
        pipe.ltrim(key, 0, self._max - 1)
        pipe.expire(key, self._ttl)
        await pipe.execute()
