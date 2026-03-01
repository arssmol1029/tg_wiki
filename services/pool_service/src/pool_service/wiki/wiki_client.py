import asyncio
import grpc
from dataclasses import dataclass
from typing import Optional

from scpedia_protos.wiki.v1 import wiki_pb2, wiki_pb2_grpc

from pool_service.domain.article import Article
from pool_service.internal.article_grpc_mapper import from_wiki_pb_article


@dataclass(frozen=True, slots=True)
class WikiClientConfig:
    target: str
    default_timeout_s: float = 2.0
    max_retries: int = 2
    retry_base_delay_s: float = 0.2


class WikiClient:

    def __init__(self, cfg: WikiClientConfig) -> None:
        self._cfg = cfg
        self._channel: grpc.aio.Channel | None = None
        self._stub: wiki_pb2_grpc.WikiServiceStub | None = None

    async def start(self) -> None:
        if self._channel is not None:
            return

        self._channel = grpc.aio.insecure_channel(
            self._cfg.target,
            options=[
                ("grpc.max_send_message_length", 10 * 1024 * 1024),
                ("grpc.max_receive_message_length", 10 * 1024 * 1024),
            ],
        )
        self._stub = wiki_pb2_grpc.WikiServiceStub(self._channel)

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
        self._channel = None
        self._stub = None

    @property
    def stub(self) -> wiki_pb2_grpc.WikiServiceStub:
        if self._stub is None:
            raise RuntimeError("WikiClient not started (call await start())")
        return self._stub

    async def _call_with_retry(self, fn, req, *, timeout_s: float | None):
        timeout = timeout_s if timeout_s is not None else self._cfg.default_timeout_s

        for attempt in range(self._cfg.max_retries + 1):
            try:
                return await fn(req, timeout=timeout)
            except grpc.aio.AioRpcError as e:
                if e.code() != grpc.StatusCode.UNAVAILABLE:
                    raise
                if attempt >= self._cfg.max_retries:
                    raise
                await asyncio.sleep(self._cfg.retry_base_delay_s * (2**attempt))

    async def get_random_article(
        self,
        *,
        min_length: int = 100,
        text: bool = True,
        image: bool = True,
        lang: str = "ru",
        timeout_s: float | None = None,
    ) -> Optional[Article]:
        if min_length < 0:
            min_length = 0

        req = wiki_pb2.GetRandomArticleRequest(
            min_length=min_length,
            text=text,
            image=image,
            lang=lang,
        )
        resp = await self._call_with_retry(
            self.stub.GetRandomArticle, req, timeout_s=timeout_s
        )
        if resp and resp.found and resp.article:
            return from_wiki_pb_article(resp.article)

        return None
