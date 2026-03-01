import os

from typing import Any, Protocol
from dataclasses import dataclass


JsonPrimitive = str | int | float | bool | None
Json = JsonPrimitive | list["Json"] | dict[str, "Json"]


@dataclass(frozen=True, slots=True)
class HttpClientConfig:
    user_agent: str = "User"
    total_timeout_s: float = 10.0
    connect_timeout_s: float = 5.0
    sock_read_timeout_s: float = 10.0

    max_connections: int = 50
    max_connections_per_host: int = 20
    ttl_dns_cache_s: int = 300

    retries: int = 2
    retry_base_delay_s: float = 0.3

    @staticmethod
    def from_env(*, prefix: str = "HTTP") -> "HttpClientConfig":
        def _get_int(name: str, default: int) -> int:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None or not raw.strip():
                return default
            try:
                return int(raw)
            except ValueError as e:
                raise ValueError(f"{name} must be an int, got: {raw!r}") from e

        def _get_float(name: str, default: float) -> float:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None or not raw.strip():
                return default
            try:
                return float(raw)
            except ValueError as e:
                raise ValueError(f"{name} must be an float, got: {raw!r}") from e

        return HttpClientConfig(
            user_agent=os.getenv(f"{prefix}_USER_AGENT", "scpedia"),
            total_timeout_s=_get_float("TOTAL_TIMEOUT", 10.0),
            connect_timeout_s=_get_float("CONNECT_TIMEOUT", 5.0),
            sock_read_timeout_s=_get_float("SOCK_READ_TIMEOUT", 10.0),
            max_connections=_get_int("MAX_CONNECTIONS", 50),
            max_connections_per_host=_get_int("MAX_CONNECTIONS_PER_HOST", 20),
            ttl_dns_cache_s=_get_int("TTL_DNS_CACHE", 300),
            retries=_get_int("RETRIES", 2),
            retry_base_delay_s=_get_float("RETRY_BASE_DELAY", 0.3),
        )


class HttpClient(Protocol):
    async def start(self) -> None: ...

    async def close(self) -> None: ...

    async def get_json(
        self, url: str, *, params: dict[str, Any] | None = None
    ) -> Json: ...

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Json: ...
