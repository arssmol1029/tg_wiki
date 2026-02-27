import asyncio
from dataclasses import dataclass
import grpc

from scpedia_protos.wiki.v1 import wiki_pb2, wiki_pb2_grpc


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
    ) -> wiki_pb2.GetArticleResponse:
        if min_length < 0:
            min_length = 0

        req = wiki_pb2.GetRandomArticleRequest(
            min_length=min_length,
            text=text,
            image=image,
            lang=lang,
        )
        return await self._call_with_retry(
            self.stub.GetRandomArticle, req, timeout_s=timeout_s
        )

    async def get_article_by_title(
        self,
        title: str,
        *,
        text: bool = True,
        image: bool = True,
        lang: str = "ru",
        timeout_s: float | None = None,
    ) -> wiki_pb2.GetArticleResponse:
        req = wiki_pb2.GetArticleByTitleRequest(
            title=title,
            text=text,
            image=image,
            lang=lang,
        )
        return await self._call_with_retry(
            self.stub.GetArticleByTitle, req, timeout_s=timeout_s
        )

    async def get_article_by_pageid(
        self,
        pageid: int,
        *,
        text: bool = True,
        image: bool = True,
        lang: str = "ru",
        timeout_s: float | None = None,
    ) -> wiki_pb2.GetArticleResponse:
        req = wiki_pb2.GetArticleByPageIdRequest(
            pageid=pageid,
            text=text,
            image=image,
            lang=lang,
        )
        return await self._call_with_retry(
            self.stub.GetArticleByPageId, req, timeout_s=timeout_s
        )

    async def search_articles(
        self,
        query: str,
        *,
        limit: int = 10,
        lang: str = "ru",
        timeout_s: float | None = None,
    ) -> wiki_pb2.SearchArticlesResponse:
        req = wiki_pb2.SearchArticlesRequest(query=query, limit=limit, lang=lang)
        return await self._call_with_retry(
            self.stub.SearchArticles, req, timeout_s=timeout_s
        )
