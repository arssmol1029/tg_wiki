import pytest

pytest.importorskip("sqlalchemy")

from datetime import datetime, timedelta, timezone

from rec_service.pool.gc_worker import GCWorker, GCWorkerConfig


def test_next_due():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert GCWorker._next_due(None, 10.0, now) == now

    last = now - timedelta(seconds=5)
    assert GCWorker._next_due(last, 10.0, now) == last + timedelta(seconds=10)

    # negative interval is clamped to 0
    assert GCWorker._next_due(last, -1.0, now) == last


@pytest.mark.asyncio
async def test_cleanup_inactive_deletes_only_extra(dummy_uow_factory, dummy_pool_repo):
    pool = dummy_pool_repo

    # lang=ru: inactive=12, max=10 -> delete 2
    pool.get_inactive_articles_count.return_value = 12
    pool.delete_articles_by_time.return_value = 2

    worker = GCWorker(
        uow_factory=lambda: dummy_uow_factory(pool=pool),  # type: ignore
        langs_map={"ru": 10},
        cfg=GCWorkerConfig(min_sleep_s=0.0),
    )

    await worker._cleanup_inactive()

    pool.get_inactive_articles_count.assert_awaited()
    pool.delete_articles_by_time.assert_awaited_with(lang="ru", count=2)
