import aiohttp
from typing import Any, Optional


DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)

HEADERS = {
    "User-Agent": "tg-wiki-bot/0.1 (https://github.com/arssmol1029/tg_wiki; contact: arssmol1029@gmail.com)"
}


async def get(
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
) -> dict:
    async with aiohttp.ClientSession(
        timeout=DEFAULT_TIMEOUT,
        headers=HEADERS,
    ) as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()
