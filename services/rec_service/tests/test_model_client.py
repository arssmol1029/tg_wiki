import pytest

pytest.importorskip("aio_pika")

from rec_service.model.model_client import ModelClient, ModelClientConfig
from rec_service.domain.article import Article
from rec_service.domain.vector import VECTOR_DIM


class DummyRPC:
    def __init__(self, result):
        self._result = result
        self.calls = []

    async def call(self, queue, *, kwargs, expiration, delivery_mode):
        self.calls.append(
            {
                "queue": queue,
                "kwargs": kwargs,
                "expiration": expiration,
                "delivery_mode": delivery_mode,
            }
        )
        return self._result


@pytest.mark.asyncio
async def test_get_embedding_requires_non_empty_extract():
    cfg = ModelClientConfig(amqp_url="amqp://guest:guest@localhost/")
    client = ModelClient(cfg)

    # Pretend client already started
    client._conn = object()  # type: ignore
    client._rpc = DummyRPC({"embedding": [0.0] * VECTOR_DIM})  # type: ignore

    with pytest.raises(ValueError):
        await client.get_embedding(
            Article(pageid=1, title="T", url="U", lang="ru", extract="")
        )


@pytest.mark.asyncio
async def test_get_embedding_handles_error_payload():
    cfg = ModelClientConfig(amqp_url="amqp://guest:guest@localhost/")
    client = ModelClient(cfg)
    client._conn = object()  # type: ignore
    client._rpc = DummyRPC({"error": "bad"})  # type: ignore

    with pytest.raises(RuntimeError):
        await client.get_embedding(
            Article(pageid=1, title="T", url="U", lang="ru", extract="text")
        )


@pytest.mark.asyncio
async def test_get_embedding_validates_vector_dim():
    cfg = ModelClientConfig(amqp_url="amqp://guest:guest@localhost/")
    client = ModelClient(cfg)
    client._conn = object()  # type: ignore
    client._rpc = DummyRPC({"embedding": [0.0] * (VECTOR_DIM - 1)})  # type: ignore

    with pytest.raises(ValueError):
        await client.get_embedding(
            Article(pageid=1, title="T", url="U", lang="ru", extract="text")
        )


@pytest.mark.asyncio
async def test_get_embedding_ok_returns_embedding():
    cfg = ModelClientConfig(amqp_url="amqp://guest:guest@localhost/", timeout_s=0.1)
    client = ModelClient(cfg)
    client._conn = object()  # type: ignore
    client._rpc = DummyRPC({"embedding": [0.0] * VECTOR_DIM})  # type: ignore

    emb = await client.get_embedding(
        Article(pageid=1, title="T", url="U", lang="ru", extract="text")
    )

    assert emb is not None
    assert len(emb.data) == VECTOR_DIM
    assert client._rpc.calls and client._rpc.calls[0]["queue"] == cfg.requests_queue  # type: ignore
