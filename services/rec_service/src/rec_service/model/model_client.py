import asyncio
import json
import uuid
import os

from dataclasses import dataclass
from datetime import timedelta

import aio_pika
from aio_pika.abc import (
    AbstractRobustConnection,
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
)

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
        self._reply_q: AbstractQueue | None = None

        self._pending: dict[str, asyncio.Future[Embedding]] = {}
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

            reply_q: AbstractQueue = await ch.declare_queue(
                exclusive=True, auto_delete=True
            )
            await reply_q.consume(self._on_reply, no_ack=False)

            self._conn = conn
            self._ch = ch
            self._reply_q = reply_q

    async def close(self) -> None:
        self._closed = True

        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(asyncio.CancelledError("ModelClient closed"))
        self._pending.clear()

        if self._conn is not None:
            await self._conn.close()

        self._conn = None
        self._ch = None
        self._reply_q = None

    async def _on_reply(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            corr_id = message.correlation_id
            if not corr_id:
                return

            fut = self._pending.pop(corr_id, None)
            if fut is None or fut.done():
                return

            try:
                payload = json.loads(message.body.decode("utf-8"))

                err = payload.get("error")
                if err:
                    fut.set_exception(RuntimeError(err))
                    return

                data = payload.get("embedding")

                if not is_valid_vector(data):
                    fut.set_exception(ValueError("Invalid embedding payload"))
                    return

                fut.set_result(Embedding(data=data).normalize())
            except Exception as e:
                fut.set_exception(e)

    async def get_embedding(self, article: Article) -> Embedding:
        if self._closed:
            raise RuntimeError("ModelClient is closed")

        if self._conn is None:
            await self.start()

        ch = self._ch
        reply_q = self._reply_q
        if ch is None or reply_q is None:
            raise RuntimeError("ModelClient not started")

        text = article.extract
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Article.extract is empty")

        request_id = str(uuid.uuid4())
        corr_id = request_id

        fut: asyncio.Future[Embedding] = asyncio.get_running_loop().create_future()
        self._pending[corr_id] = fut

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

        msg = aio_pika.Message(
            body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            correlation_id=corr_id,
            reply_to=reply_q.name,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            expiration=timedelta(milliseconds=expiration_ms),
        )

        try:
            await ch.default_exchange.publish(msg, routing_key=self._cfg.requests_queue)
            return await asyncio.wait_for(fut, timeout=self._cfg.timeout_s)
        except Exception:
            self._pending.pop(corr_id, None)
            raise
