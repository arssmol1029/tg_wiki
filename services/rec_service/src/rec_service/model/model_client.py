import asyncio
import os
import uuid
from dataclasses import dataclass

import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractChannel
from aio_pika.patterns import RPC, JsonRPC

from rec_service.domain.article import Article
from rec_service.domain.embedding import Embedding
from rec_service.domain.vector import is_valid_vector


@dataclass(frozen=True, slots=True)
class ModelClientConfig:
    amqp_url: str
    requests_queue: str = "model.embed.requests"
    timeout_s: float = 30.0
    prefetch: int = 200
    expiration_ms: int | None = None

    @staticmethod
    def from_env(*, prefix: str = "MODEL") -> "ModelClientConfig":
        amqp_url = os.getenv(f"{prefix}_AMQP_URL", "").strip()
        if not amqp_url:
            raise ValueError("AMQP_URL is required to enable model client")

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

        return ModelClientConfig(
            amqp_url=amqp_url,
            requests_queue=os.getenv(
                f"{prefix}_REQUESTS_QUEUE", "model.embed.requests"
            ),
            timeout_s=_get_float("TIMEOUT", 30.0),
            prefetch=_get_int("PREFETCH", 200),
            expiration_ms=_get_int("EXPIRATION", 0) or None,
        )


class ModelClient:
    def __init__(self, cfg: ModelClientConfig | None = None):
        self._cfg = cfg or ModelClientConfig.from_env()

        self._conn: AbstractRobustConnection | None = None
        self._ch: AbstractChannel | None = None
        self._rpc: RPC | None = None

        self._start_lock = asyncio.Lock()
        self._closed = False

    async def start(self) -> None:
        if self._closed:
            raise RuntimeError("ModelClient is closed")

        if self._conn is not None:
            return

        async with self._start_lock:
            if self._conn is not None:
                return

            conn: AbstractRobustConnection = await aio_pika.connect_robust(
                self._cfg.amqp_url
            )
            ch: AbstractChannel = await conn.channel()
            await ch.set_qos(prefetch_count=self._cfg.prefetch)

            await ch.declare_queue(self._cfg.requests_queue, durable=True)

            rpc = await JsonRPC.create(ch)

            self._conn = conn
            self._ch = ch
            self._rpc = rpc

    async def close(self) -> None:
        self._closed = True
        if self._conn is not None:
            await self._conn.close()

        self._conn = None
        self._ch = None
        self._rpc = None

    async def get_embedding(self, article: Article) -> Embedding:
        if self._closed:
            raise RuntimeError("ModelClient is closed")

        if self._conn is None:
            await self.start()

        rpc = self._rpc
        if rpc is None:
            raise RuntimeError("ModelClient not started")

        text = article.extract
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Article.extract is empty")

        request_id = str(uuid.uuid4())
        body = {
            "request_id": request_id,
            "text": text,
            "meta": {
                "lang": article.lang,
                "page_id": int(article.pageid),
                "title": article.title,
            },
        }

        expiration_ms = self._cfg.expiration_ms
        if expiration_ms is None:
            expiration_ms = int((self._cfg.timeout_s + 5.0) * 1000)

        try:
            result = await asyncio.wait_for(
                rpc.call(
                    self._cfg.requests_queue,
                    kwargs=body,
                    expiration=expiration_ms,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                timeout=self._cfg.timeout_s,
            )
        except Exception:
            raise

        if isinstance(result, dict):
            err = result.get("error")
            if err:
                raise RuntimeError(str(err))

            data = result.get("embedding")
        else:
            data = None

        if not is_valid_vector(data):
            raise ValueError("Invalid embedding payload")

        return Embedding(data=data).normalize()
