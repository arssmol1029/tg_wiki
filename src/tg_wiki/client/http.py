from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Final

import aiohttp


Json = dict[str, Any] | list[Any]


class HttpClientError(RuntimeError):
    """Base error for HTTP client failures."""


class HttpNotStartedError(HttpClientError):
    """Raised when client session is not started."""


class HttpRequestError(HttpClientError):
    """Network/transport or response parse errors."""


@dataclass(frozen=True, slots=True)
class HttpClientConfig:
    user_agent: str = "tg_wiki_bot/0.1 (contact: arssmol1029@gmail.com)"
    total_timeout_sec: float = 10.0
    connect_timeout_sec: float = 5.0
    sock_read_timeout_sec: float = 10.0

    max_connections: int = 50
    max_connections_per_host: int = 20
    ttl_dns_cache_sec: int = 300

    retries: int = 2
    retry_base_delay_sec: float = 0.3


class HttpClient:
    def __init__(self, config: HttpClientConfig | None = None) -> None:
        self._cfg: Final[HttpClientConfig] = config or HttpClientConfig()
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            raise HttpNotStartedError("HttpClient is not started. Call await start().")
        return self._session

    async def start(self) -> None:
        if self._session is not None and not self._session.closed:
            return

        timeout = aiohttp.ClientTimeout(
            total=self._cfg.total_timeout_sec,
            connect=self._cfg.connect_timeout_sec,
            sock_read=self._cfg.sock_read_timeout_sec,
        )

        connector = aiohttp.TCPConnector(
            limit=self._cfg.max_connections,
            limit_per_host=self._cfg.max_connections_per_host,
            ttl_dns_cache=self._cfg.ttl_dns_cache_sec,
        )

        headers = {
            "User-Agent": self._cfg.user_agent,
            "Accept": "application/json",
        }

        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=headers,
            raise_for_status=False,
        )

    async def close(self) -> None:
        if self._session is None:
            return
        await self._session.close()
        self._session = None

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Json:
        return await self.request_json("GET", url, params=params)

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Json:
        last_exc: Exception | None = None
        for attempt in range(self._cfg.retries + 1):
            try:
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                ) as resp:
                    if resp.status == 429 or 500 <= resp.status <= 599:
                        raise HttpRequestError(f"Transient HTTP status: {resp.status}")

                    if resp.status < 200 or resp.status >= 300:
                        text = await resp.text()
                        raise HttpRequestError(f"HTTP {resp.status}: {text[:300]}")

                    try:
                        return await resp.json()
                    except aiohttp.ContentTypeError as e:
                        text = await resp.text()
                        raise HttpRequestError(
                            f"Invalid JSON response: {text[:300]}"
                        ) from e

            except (aiohttp.ClientError, asyncio.TimeoutError, HttpRequestError) as e:
                last_exc = e
                if attempt >= self._cfg.retries:
                    break
                await asyncio.sleep(self._cfg.retry_base_delay_sec * (2**attempt))

        raise HttpRequestError("HTTP request failed") from last_exc
