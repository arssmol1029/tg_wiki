from typing import Any, Protocol
from dataclasses import dataclass


JsonPrimitive = str | int | float | bool | None
Json = JsonPrimitive | list["Json"] | dict[str, "Json"]


@dataclass(frozen=True, slots=True)
class HttpClientConfig:
    user_agent: str = "User"
    total_timeout_sec: float = 10.0
    connect_timeout_sec: float = 5.0
    sock_read_timeout_sec: float = 10.0

    max_connections: int = 50
    max_connections_per_host: int = 20
    ttl_dns_cache_sec: int = 300

    retries: int = 2
    retry_base_delay_sec: float = 0.3


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
