import pytest
import pytest_asyncio

grpc = pytest.importorskip("grpc")

pytest.importorskip("scpedia_protos.rec.v1.rec_pb2")

from unittest.mock import AsyncMock

from scpedia_protos.rec.v1 import rec_pb2, rec_pb2_grpc

from rec_service.grpc_server import RecGrpcServicer
from rec_service.domain.article import Article
from rec_service.domain.preference import Preference
from rec_service.domain.embedding import Embedding
from rec_service.domain.vector import VECTOR_DIM


@pytest_asyncio.fixture
async def grpc_stub(monkeypatch):
    import rec_service.grpc_server as server_mod

    monkeypatch.setattr(server_mod, "is_supported_lang", lambda lang: lang == "ru")
    monkeypatch.setattr(server_mod, "supported_langs_list", lambda: ("ru",))

    rec_svc = AsyncMock()
    pool_svc = AsyncMock()

    server = grpc.aio.server()
    rec_pb2_grpc.add_RecServiceServicer_to_server(
        RecGrpcServicer(rec_svc, pool_svc),
        server,
    )

    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = rec_pb2_grpc.RecServiceStub(channel)

    try:
        yield stub, rec_svc, pool_svc
    finally:
        await channel.close()
        await server.stop(grace=0)


@pytest.mark.asyncio
async def test_grpc_get_article_ok(grpc_stub):
    stub, rec_svc, pool_svc = grpc_stub

    rec_svc.get_user_pref = AsyncMock(return_value=Preference())
    pool_svc.get_best_articles = AsyncMock(
        return_value=[
            Article(
                pageid=1,
                title="T",
                url="U",
                lang="ru",
                thumbnail_url="IMG",
                extract="hello",
            )
        ]
    )

    req = rec_pb2.GetArticleRequest(
        userid=1, lang="ru", count=1, text=False, image=False
    )
    resp = await stub.GetArticle(req, timeout=1.0)

    assert len(resp.articles) == 1
    assert resp.articles[0].pageid == 1
    assert resp.articles[0].lang == "ru"
    assert resp.articles[0].extract == ""  # text=False
    assert resp.articles[0].thumbnail_url == ""  # image=False


@pytest.mark.asyncio
async def test_grpc_get_article_invalid_lang(grpc_stub, monkeypatch):
    stub, _rec_svc, _pool_svc = grpc_stub

    import rec_service.grpc_server as server_mod

    monkeypatch.setattr(server_mod, "is_supported_lang", lambda lang: False)
    monkeypatch.setattr(server_mod, "supported_langs_list", lambda: ("ru", "en"))

    req = rec_pb2.GetArticleRequest(userid=1, lang="xx", count=1, text=True, image=True)

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetArticle(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_grpc_get_article_min_length_negative_is_invalid_argument(grpc_stub):
    stub, rec_svc, _pool_svc = grpc_stub

    rec_svc.get_user_pref = AsyncMock(return_value=Preference())

    req = rec_pb2.GetArticleRequest(
        userid=1,
        lang="ru",
        count=1,
        min_length=-1,
        text=True,
        image=True,
    )

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.GetArticle(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_grpc_update_preference_ok(grpc_stub):
    stub, rec_svc, pool_svc = grpc_stub

    rec_svc.get_user_pref = AsyncMock(return_value=Preference())
    pool_svc.get_article_embedding = AsyncMock(
        return_value=Embedding([0.0] * VECTOR_DIM)
    )
    rec_svc.get_user_calibration_size = AsyncMock(return_value=0)
    rec_svc.get_user_total_seen = AsyncMock(return_value=0)
    rec_svc.update_user_pref = AsyncMock(return_value=True)

    req = rec_pb2.UpdatePreferenceRequest(userid=1, lang="ru", pageid=10, reaction=1)
    resp = await stub.UpdatePreference(req, timeout=1.0)

    assert resp.success is True


@pytest.mark.asyncio
async def test_grpc_update_preference_store_failure_is_internal(grpc_stub):
    stub, rec_svc, pool_svc = grpc_stub

    rec_svc.get_user_pref = AsyncMock(return_value=Preference())
    pool_svc.get_article_embedding = AsyncMock(
        return_value=Embedding([0.0] * VECTOR_DIM)
    )
    rec_svc.get_user_calibration_size = AsyncMock(return_value=0)
    rec_svc.get_user_total_seen = AsyncMock(return_value=0)
    rec_svc.update_user_pref = AsyncMock(return_value=False)

    req = rec_pb2.UpdatePreferenceRequest(userid=1, lang="ru", pageid=10, reaction=1)

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.UpdatePreference(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.INTERNAL


@pytest.mark.asyncio
async def test_grpc_create_user_invalid_calibration_size(grpc_stub):
    stub, _rec_svc, _pool_svc = grpc_stub

    req = rec_pb2.UpsertUserRequest(userid=1, calibration_size=-1)

    with pytest.raises(grpc.aio.AioRpcError) as err:
        await stub.CreateUser(req, timeout=1.0)

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT
