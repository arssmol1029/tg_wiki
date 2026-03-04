import asyncio
import os
import signal

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from rec_service.database.config import DBConfig
from rec_service.database.ports import Uow
from rec_service.database.session import create_sessionmaker, create_engine
from rec_service.database.postgres.postgres import make_uow_factory
from rec_service.internal.langs import init_langs, extra_size_per_lang
from rec_service.internal.logging import setup_logging, get_logger


log = get_logger(__name__, component="gc-worker")


@dataclass(frozen=True, slots=True)
class GCWorkerConfig:
    quarantine_max_age_s: float = 30 * 24 * 60 * 60.0  # month

    quarantine_cleanup_interval_s: float = 24 * 60 * 60.0  # day

    inactive_cleanup_interval_s: float = 10 * 60.0

    min_sleep_s: float = 0.2

    @staticmethod
    def from_env(*, prefix: str = "GCWorker") -> "GCWorkerConfig":
        def _get_float(name: str, default: float) -> float:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None or not raw.strip():
                return default
            try:
                return float(raw)
            except ValueError as e:
                raise ValueError(f"{name} must be a float, got: {raw!r}") from e

        return GCWorkerConfig(
            quarantine_max_age_s=_get_float("QUARANTINE_MAX_AGE", 30 * 24 * 60 * 60.0),
            quarantine_cleanup_interval_s=_get_float(
                "QUARANTINE_CLEANUP_INTERVAL", 24 * 60 * 60.0
            ),
            inactive_cleanup_interval_s=_get_float(
                "INACTIVE_CLEANUP_INTERVAL", 10 * 60.0
            ),
            min_sleep_s=_get_float("MIN_SLEEP", 0.2),
        )


class GCWorker:
    def __init__(
        self,
        *,
        uow_factory: Callable[[], Uow],
        langs_map: dict[str, int],
        cfg: GCWorkerConfig | None = None,
    ):
        self._uow_factory = uow_factory
        self._langs_map = dict(langs_map)
        self._cfg = cfg or GCWorkerConfig.from_env()

        self._last_quarantine_cleanup: datetime | None = None
        self._last_inactive_cleanup: datetime | None = None

    async def run(self) -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass

        await self._cleanup_quarantine()
        await self._cleanup_inactive()

        while not stop.is_set():
            now = datetime.now(timezone.utc)

            next_q = self._next_due(
                self._last_quarantine_cleanup,
                self._cfg.quarantine_cleanup_interval_s,
                now,
            )
            next_i = self._next_due(
                self._last_inactive_cleanup, self._cfg.inactive_cleanup_interval_s, now
            )
            next_due = min(next_q, next_i)

            if next_due <= now:
                if next_q <= now:
                    await self._cleanup_quarantine()
                if next_i <= now:
                    await self._cleanup_inactive()
                continue

            sleep_s = (next_due - now).total_seconds()
            sleep_s = max(self._cfg.min_sleep_s, sleep_s)
            try:
                await asyncio.wait_for(stop.wait(), timeout=sleep_s)
            except asyncio.TimeoutError:
                continue

    @staticmethod
    def _next_due(last: datetime | None, interval_s: float, now: datetime) -> datetime:
        if last is None:
            return now
        return last + timedelta(seconds=max(interval_s, 0.0))

    async def _cleanup_quarantine(self) -> None:
        now = datetime.now(timezone.utc)
        deadline = now - timedelta(seconds=max(self._cfg.quarantine_max_age_s, 0.0))

        async with self._uow_factory() as uow:
            released_count = await uow.quarantine.release_by_time(deadline=deadline)

        log.info("Released %d articles from quarantine", released_count)

        self._last_quarantine_cleanup = now

    async def _cleanup_inactive(self) -> None:
        """
        Leave only inactive articles per language under langs_map[lang] by deleting oldest inactive articles.
        """
        now = datetime.now(timezone.utc)

        for lang, max_inactive in self._langs_map.items():
            if max_inactive < 0:
                continue

            async with self._uow_factory() as uow:
                inactive = await uow.pool.get_inactive_articles_count(lang=lang)
                extra = int(inactive) - int(max_inactive)
                if extra <= 0:
                    continue

                deleated_count = await uow.pool.delete_articles_by_time(
                    lang=lang, count=extra
                )

            log.info("Deleated %d inactive articles for lang=%s", deleated_count, lang)

        self._last_inactive_cleanup = now


async def _main() -> None:
    init_langs(csv_path=os.getenv("PATH_TO_LANGS", "langs.csv"))
    setup_logging()

    gc_worker_cfg = GCWorkerConfig.from_env()

    db_config = DBConfig.from_env()
    engine = create_engine(db_config)
    uow_factory = make_uow_factory(create_sessionmaker(engine))

    gc_worker = GCWorker(
        uow_factory=uow_factory, langs_map=extra_size_per_lang(), cfg=gc_worker_cfg
    )
    log.info("Starting gc worker...")
    await gc_worker.run()


# entrypoint: rec_service.workers.gc_worker
def run() -> None:
    asyncio.run(_main())
