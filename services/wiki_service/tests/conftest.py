import pytest

from wiki_service.service.wiki_service import WikiService


class DummyHttp:
    async def get_json(self, url: str, *, params=None):
        raise AssertionError(
            "DummyHttp.get_json was called unexpectedly. Did you forget monkeypatch?"
        )

    async def request_json(
        self, method: str, url: str, *, params=None, json=None, headers=None
    ):
        raise AssertionError(
            "DummyHttp.request_json was called unexpectedly. Did you forget monkeypatch?"
        )

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None


@pytest.fixture
def http() -> DummyHttp:
    return DummyHttp()


@pytest.fixture
def svc(http) -> WikiService:
    return WikiService(http)
