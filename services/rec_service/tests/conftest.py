import pytest

from unittest.mock import AsyncMock


class DummyUserRepo:
    def __init__(self):
        self.create_user = AsyncMock()
        self.get_user_pref = AsyncMock()
        self.get_user_calibration_size = AsyncMock()
        self.get_user_total_seen = AsyncMock()
        self.update_user_pref = AsyncMock()
        self.reset_user = AsyncMock()
        self.delete_user = AsyncMock()
        self.get_max_user_seen = AsyncMock()


@pytest.fixture
def dummy_user_repo():
    return DummyUserRepo()


class DummyPoolRepo:
    def __init__(self):
        self.add_articles = AsyncMock()
        self.add_article = AsyncMock()
        self.get_articles_by_pageids = AsyncMock()
        self.get_article_by_pageid = AsyncMock()
        self.get_best_articles = AsyncMock()
        self.get_active_articles_count = AsyncMock()
        self.get_inactive_articles_count = AsyncMock()
        self.set_articles_active = AsyncMock()
        self.get_article_embedding = AsyncMock()
        self.delete_articles = AsyncMock()
        self.delete_article = AsyncMock()
        self.delete_articles_by_time = AsyncMock()


@pytest.fixture
def dummy_pool_repo():
    return DummyPoolRepo()


class DummyQuarantineRepo:
    def __init__(self):
        self.filter_not_quarantined = AsyncMock()
        self.add_articles = AsyncMock()
        self.release_by_time = AsyncMock()


@pytest.fixture
def dummy_quarantine_repo():
    return DummyQuarantineRepo()


class DummyUow:
    def __init__(self, users, pool, quarantine):
        self.users = users
        self.pool = pool
        self.quarantine = quarantine

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.fixture
def dummy_uow_factory():
    def _make(users=None, pool=None, quarantine=None):
        return DummyUow(users, pool, quarantine)

    return _make
