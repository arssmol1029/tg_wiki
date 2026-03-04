import asyncio
import inspect
import os
import random
import signal

from dataclasses import dataclass
from typing import Callable, Sequence

from rec_service.database.config import DBConfig
from rec_service.database.ports import Uow
from rec_service.database.session import create_sessionmaker, create_engine
from rec_service.database.postgres.postgres import make_uow_factory
from rec_service.domain.article import Article
from rec_service.domain.embedding import Embedding
from rec_service.internal.article_db_mapper import article_to_insert
from rec_service.internal.langs import init_langs, pool_size_per_lang
from rec_service.model.model_client import ModelClient, ModelClientConfig
from rec_service.wiki.wiki_client import WikiClient, WikiClientConfig
from rec_service.internal.logging import setup_logging, get_logger


log = get_logger(__name__, component="refresh-worker")


@dataclass(frozen=True, slots=True)
class RefreshWorkerConfig:
    max_user_seen_threshold: int = 100

    articles_to_replace: int = 50

    check_cooldown_s: float = 60.0

    wiki_timeout_s: float = 5.0
    embed_timeout_s: float = 10.0

    max_inflight: int = 10

    wiki_concurrency: int = 10
    embed_concurrency: int = 5

    max_attempts_multiplier: int = 5

    backoff_s: float = 0.05

    quarantine_on_insert: bool = True

    @staticmethod
    def from_env(*, prefix: str = "REFRESH_WORKER") -> "RefreshWorkerConfig":
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
                raise ValueError(f"{name} must be a float, got: {raw!r}") from e

        def _get_bool(name: str, default: bool) -> bool:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None or not raw.strip():
                return default
            v = raw.strip().lower()
            if v in {"1", "true", "yes", "y", "on"}:
                return True
            if v in {"0", "false", "no", "n", "off"}:
                return False
            raise ValueError(f"{name} must be a bool-ish string, got: {raw!r}")

        return RefreshWorkerConfig(
            max_user_seen_threshold=_get_int("MAX_USER_SEEN_THRESHOLD", 100),
            articles_to_replace=_get_int("ARTICLES_TO_REPLACE", 50),
            check_cooldown_s=_get_float("CHECK_INTERVAL_S", 60.0),
            wiki_timeout_s=_get_float("WIKI_TIMEOUT", 5.0),
            embed_timeout_s=_get_float("MODEL_TIMEOUT", 10.0),
            max_inflight=_get_int("MAX_INFLIGHT", 10),
            wiki_concurrency=_get_int("WIKI_CONCURRENCY", 10),
            embed_concurrency=_get_int("MODEL_CONCURRENCY", 5),
            max_attempts_multiplier=_get_int("MAX_ATTEMPTS_MULTIPLIER", 5),
            backoff_s=_get_float("BACKOFF", 0.05),
            quarantine_on_insert=_get_bool("QUARANTINE_ON_INSERT", True),
        )


class RefreshWorker:
    def __init__(
        self,
        *,
        wiki: WikiClient,
        model: ModelClient,
        uow_factory: Callable[[], Uow],
        langs_map: dict[str, int],
        cfg: RefreshWorkerConfig | None = None,
    ):
        self._wiki = wiki
        self._model = model
        self._uow_factory = uow_factory
        self._langs_map = dict(langs_map)
        self._cfg = cfg or RefreshWorkerConfig.from_env()

        self._wiki_sem = asyncio.Semaphore(self._cfg.wiki_concurrency)
        self._emb_sem = asyncio.Semaphore(self._cfg.embed_concurrency)

        self._op_lock = asyncio.Lock()

    async def run(self) -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass

        while not stop.is_set():
            did_work = False
            try:
                lang = self._choose_lang_weighted()
                did_work = await self._tick(lang=lang)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Tick failed for lang=%s", lang)
                did_work = False

            if not did_work:
                await asyncio.sleep(self._cfg.check_cooldown_s)

    def _choose_lang_weighted(self) -> str:
        langs = list(self._langs_map)
        weights = [self._langs_map[l] for l in langs]
        return random.choices(langs, weights=weights, k=1)[0]

    async def _tick(self, *, lang: str) -> bool:
        if self._op_lock.locked():
            return False

        async with self._op_lock:
            target = self._langs_map[lang]

            async with self._uow_factory() as uow:
                current = await uow.pool.get_active_articles_count(lang=lang)

            if current < target:
                deficit = target - current
                await self._fill_to_target(lang=lang, deficit=deficit)
                return True

            async with self._uow_factory() as uow:
                seen_pageids = await uow.users.get_max_user_seen(lang=lang)

            if len(seen_pageids) <= self._cfg.max_user_seen_threshold:
                return False

            pageids_to_replace = seen_pageids[: max(1, self._cfg.articles_to_replace)]
            await self._deactivate_and_refill(
                lang=lang, pageids_to_replace=pageids_to_replace
            )

            return True

    async def _deactivate_and_refill(
        self, *, lang: str, pageids_to_replace: Sequence[int]
    ) -> None:
        """
        Refill database by replace old articles with new ones.
        """
        inserted_count = await self._fill_to_target(
            lang=lang, deficit=len(pageids_to_replace)
        )

        async with self._uow_factory() as uow:
            await uow.pool.set_articles_active(
                lang=lang, pageids=pageids_to_replace[:inserted_count], is_active=False
            )
        log.info("Replased %d articles", inserted_count)

    async def _fill_to_target(self, *, lang: str, deficit: int) -> int:
        """
        Fetch the required number of articles + embeddings and fill the database.
        """
        if deficit <= 0:
            return 0

        inserted_count = 0
        attempts = 0
        max_attempts = max(1, self._cfg.max_attempts_multiplier) * deficit

        seen_pageids: set[int] = set()

        while inserted_count < deficit and attempts < max_attempts:
            need = deficit - inserted_count
            inflight = min(need, self._cfg.max_inflight)

            candidates = await self._fetch_candidates(
                lang=lang, count=inflight, seen_pageids=seen_pageids
            )
            attempts += inflight

            if not candidates:
                await asyncio.sleep(self._cfg.backoff_s)
                continue

            pageids = [a.pageid for a in candidates]
            async with self._uow_factory() as uow:
                allowed = await uow.quarantine.filter_not_quarantined(
                    lang=lang, pageids=pageids
                )
            allowed_set = set(allowed)
            allowed_articles = [a for a in candidates if a.pageid in allowed_set]

            if not allowed_articles:
                await asyncio.sleep(self._cfg.backoff_s)
                continue

            pairs = await self._embed_many(lang=lang, articles=allowed_articles)
            if not pairs:
                await asyncio.sleep(self._cfg.backoff_s)
                continue

            async with self._uow_factory() as uow:
                inserted_pageids = await uow.pool.add_articles(
                    articles=[
                        article_to_insert(article=article, embedding=embedding)
                        for article, embedding in pairs
                    ]
                )
                inserted_count += len(inserted_pageids)

                if self._cfg.quarantine_on_insert and inserted_pageids:
                    await uow.quarantine.add_articles(
                        lang=lang, pageids=inserted_pageids
                    )

        log.info("Inserted %d articles with %d attempts", inserted_count, attempts)
        return inserted_count

    async def _fetch_candidates(
        self, *, lang: str, count: int, seen_pageids: set[int]
    ) -> list[Article]:
        async def one() -> Article | None:
            async with self._wiki_sem:
                try:
                    return await self._wiki.get_random_article(
                        min_length=0,
                        lang=lang,
                        text=True,
                        image=True,
                        timeout_s=self._cfg.wiki_timeout_s,
                    )
                except Exception:
                    log.warning(
                        "Fetch wiki article failed for lang=%s", lang, exc_info=True
                    )
                    return None

        tasks = [asyncio.create_task(one()) for _ in range(count)]
        res = await asyncio.gather(*tasks, return_exceptions=True)

        log.info(
            "Requested %d wiki pages, get %d (batch=%d)",
            count,
            len(res),
            self._cfg.wiki_concurrency,
        )

        out: list[Article] = []
        for r in res:
            if not isinstance(r, Article):
                continue
            if r.pageid in seen_pageids:
                continue
            seen_pageids.add(r.pageid)
            out.append(r)

        return out

    async def _embed_many(
        self, *, lang: str, articles: Sequence[Article]
    ) -> list[tuple[Article, Embedding]]:
        async def one(article: Article) -> tuple[Article, Embedding] | None:
            async with self._emb_sem:
                try:
                    emb = await asyncio.wait_for(
                        self._maybe_await_embedding(article),
                        timeout=self._cfg.embed_timeout_s,
                    )
                    return (article, emb)
                except Exception:
                    log.warning(
                        "Compute embedding failed for lang=%s", lang, exc_info=True
                    )
                    return None

        tasks = [asyncio.create_task(one(a)) for a in articles]
        res = await asyncio.gather(*tasks, return_exceptions=False)

        log.info(
            "Computed %d embeddings, get %d (batch=%d)",
            len(articles),
            len(res),
            self._cfg.wiki_concurrency,
        )

        return [r for r in res if r is not None]

    async def _maybe_await_embedding(self, article: Article) -> Embedding:
        res = self._model.get_embedding(article)
        if inspect.isawaitable(res):
            return await res
        return res


async def _main() -> None:
    init_langs(csv_path=os.getenv("PATH_TO_LANGS", "langs.csv"))
    setup_logging()

    refresh_worker_cfg = RefreshWorkerConfig.from_env()
    wiki_client_cfg = WikiClientConfig.from_env()
    model_client_cfg = ModelClientConfig.from_env()

    wiki: WikiClient | None = None
    model: ModelClient | None = None

    try:
        wiki = WikiClient(wiki_client_cfg)
        log.info("Starting wiki client...")
        await wiki.start()

        model = ModelClient(model_client_cfg)
        log.info("Starting model client...")
        await model.start()

        db_config = DBConfig.from_env()
        engine = create_engine(db_config)
        uow_factory = make_uow_factory(create_sessionmaker(engine))

        refresh_worker = RefreshWorker(
            wiki=wiki,
            model=model,
            uow_factory=uow_factory,
            langs_map=pool_size_per_lang(),
            cfg=refresh_worker_cfg,
        )
        log.info("Starting refresh worker...")
        await refresh_worker.run()
    finally:
        if wiki:
            await wiki.close()
        if model:
            await model.close()


# entrypoint: rec_service.workers.refresh_worker
def run() -> None:
    asyncio.run(_main())
