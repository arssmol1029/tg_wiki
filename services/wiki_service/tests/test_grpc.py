import asyncio
import pytest_asyncio, pytest
import grpc
from unittest.mock import AsyncMock

from scpedia_protos.wiki.v1 import wiki_pb2, wiki_pb2_grpc

from wiki_service.internal.errors import HttpRequestError
from wiki_service.domain.article import to_pb_meta, to_pb_article
from wiki_service.grpc_server import WikiGrpcServicer
from wiki_service.service.wiki_service import Article, ArticleMeta


@pytest_asyncio.fixture
async def grpc_stub():
    """
    Up gRPC server

    Returns:
        (stub, svc_mock, server, channel)
    """
    svc = AsyncMock()

    server = grpc.aio.server()
    wiki_pb2_grpc.add_WikiServiceServicer_to_server(WikiGrpcServicer(svc), server)

    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = wiki_pb2_grpc.WikiServiceStub(channel)

    try:
        yield stub, svc
    finally:
        await channel.close()
        await server.stop(grace=0)


@pytest.mark.asyncio
async def test_grpc_get_ok(grpc_stub):
    stub, svc = grpc_stub

    svc.get_article_by_title = AsyncMock(
        return_value=Article(
            meta=ArticleMeta(pageid=1, title="T", url="U", thumbnail_url=None),
            extract="hello",
            lang="ru",
        )
    )

    req = wiki_pb2.GetArticleByTitleRequest(
        title="T", text=True, image=False, lang="ru"
    )
    resp = await stub.GetArticleByTitle(req, timeout=1.0)

    assert resp.found is True
    assert resp.article.meta.pageid == 1
    assert resp.article.meta.title == "T"
    assert resp.article.lang == "ru"
    assert resp.article.extract == "hello"


@pytest.mark.asyncio
async def test_grpc_get_not_found(grpc_stub):
    stub, svc = grpc_stub

    # PageId/Title -> Expect StatusCode.NOT_FOUND
    svc.get_article_by_pageid = AsyncMock(return_value=None)

    req = wiki_pb2.GetArticleByPageIdRequest(pageid=1, text=True, image=True, lang="ru")

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetArticleByPageId(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.NOT_FOUND

    # Random -> Expect resp.found == False
    svc.get_random_article = AsyncMock(return_value=None)

    req = wiki_pb2.GetRandomArticleRequest(text=True, image=True, lang="ru")

    resp = await stub.GetRandomArticle(req, timeout=1.0)

    assert resp.found == False


@pytest.mark.asyncio
async def test_grpc_get_invalid_argument(grpc_stub):
    stub, _svc = grpc_stub

    req = wiki_pb2.GetArticleByTitleRequest(
        title="   ", text=True, image=True, lang="ru"
    )

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetArticleByTitle(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_grpc_http_429_maps_to_resource_exhausted(grpc_stub):
    stub, svc = grpc_stub

    svc.get_article_by_title = AsyncMock(
        side_effect=HttpRequestError("rate limit", status_code=429, is_transient=True)
    )

    req = wiki_pb2.GetArticleByTitleRequest(title="T", text=True, image=True, lang="ru")

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetArticleByTitle(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED


@pytest.mark.asyncio
async def test_grpc_transport_error_maps_to_unavailable(grpc_stub):
    stub, svc = grpc_stub

    svc.get_article_by_pageid = AsyncMock(
        side_effect=HttpRequestError("timeout", status_code=None, is_transient=True)
    )

    req = wiki_pb2.GetArticleByPageIdRequest(pageid=1, text=True, image=True, lang="ru")

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetArticleByPageId(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.UNAVAILABLE


@pytest.mark.asyncio
async def test_grpc_deadline_exceeded(grpc_stub):
    stub, svc = grpc_stub

    async def slow(*args, **kwargs):
        await asyncio.sleep(0.05)
        return None

    svc.get_article_by_title = AsyncMock(side_effect=slow)

    req = wiki_pb2.GetArticleByTitleRequest(title="T", text=True, image=True, lang="ru")

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetArticleByTitle(req, timeout=0.001)

    assert err.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED
