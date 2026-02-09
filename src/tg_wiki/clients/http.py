import aiohttp
from typing import Any, Optional


DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def get(
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
) -> dict:
    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()
