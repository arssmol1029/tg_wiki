from dataclasses import dataclass
import asyncio
import inspect
from typing import Iterable, Callable

from pool_service.database.ports import Uow
from pool_service.domain.article import Article, PooledArticle
from pool_service.domain.embedding import EmbeddingVector
from pool_service.wiki.wiki_client import WikiClient
from pool_service.model.model_client import ModelClient


@dataclass(frozen=True, slots=True)
class PoolWorkerConfig:
    concurrency: int = 10
    max_attempts_multiplier: int = 5
    max_inflight: int = 50
    min_inflight: int = 20


class PoolWorker:
    def __init__(
        self,
        *,
        wiki: WikiClient,
        model: ModelClient,
        uow_factory: Callable[[], Uow],
        cfg: PoolWorkerConfig | None = None,
    ):
        self._wiki = wiki
        self._model = model
        self._uow_factory = uow_factory
        self._cfg = cfg or PoolWorkerConfig()

    async def produce_batch(
        self,
        n: int,
        *,
        lang: str,
        min_length: int = 0,
        image: bool = True,
        wiki_timeout_s: float | None = None,
        max_inflight: int | None = None,
        min_inflight: int | None = None,
    ) -> list[PooledArticle]:
        if n <= 0:
            return []

        if min_inflight is None:
            min_inflight = self._cfg.min_inflight
        min_inflight = max(min_inflight, 1)

        if max_inflight is None:
            max_inflight = self._cfg.max_inflight
        max_inflight = max(max_inflight, min_inflight)

        wiki_sem = asyncio.Semaphore(self._cfg.concurrency)
        seen: set[int] = set()
        out: list[PooledArticle] = []
        pending: dict[asyncio.Task[EmbeddingVector], Article] = {}

        max_attempts = n * self._cfg.max_attempts_multiplier
        attempts = 0

        async def fetch_one() -> Article | None:
            async with wiki_sem:
                return await self._wiki.get_random_article(
                    min_length=min_length,
                    lang=lang,
                    text=True,
                    image=image,
                    timeout_s=wiki_timeout_s,
                )

        def _launch_embedding(article: Article) -> None:
            t: asyncio.Task[EmbeddingVector] = asyncio.create_task(
                self._maybe_await_embedding(article)
            )
            pending[t] = article

        def _harvest_done(
            *, done_tasks: Iterable[asyncio.Task[EmbeddingVector]]
        ) -> None:
            for t in done_tasks:
                article = pending.pop(t, None)
                if article is None:
                    continue
                try:
                    emb = t.result()
                except Exception:
                    continue
                out.append(PooledArticle(article, embedding=emb))

        async def _drain_ready_now() -> None:
            if not pending:
                return
            done = [t for t in pending.keys() if t.done()]
            if done:
                _harvest_done(done_tasks=done)

        try:
            while len(out) < n and (attempts < max_attempts or pending):
                await _drain_ready_now()
                if len(out) >= n:
                    break

                if attempts >= max_attempts:
                    if not pending:
                        break
                    done, _ = await asyncio.wait(
                        set(pending.keys()),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    _harvest_done(done_tasks=done)
                    continue

                inflight_budget = max_inflight - len(pending)
                if inflight_budget < min_inflight:
                    if pending:
                        done, _ = await asyncio.wait(
                            set(pending.keys()),
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        _harvest_done(done_tasks=done)
                    continue

                target = min(inflight_budget, max_attempts - attempts)
                if target <= 0:
                    if pending:
                        done, _ = await asyncio.wait(
                            set(pending.keys()), return_when=asyncio.FIRST_COMPLETED
                        )
                        _harvest_done(done_tasks=done)
                    continue

                candidates: list[Article] = []
                candidate_ids: list[int] = []

                while len(candidates) < target and attempts < max_attempts:
                    round_size = min(self._cfg.concurrency, target - len(candidates))
                    results = await asyncio.gather(
                        *(fetch_one() for _ in range(round_size)),
                        return_exceptions=True,
                    )
                    attempts += round_size

                    for r in results:
                        if isinstance(r, BaseException) or r is None:
                            continue
                        pid = int(r.meta.pageid)
                        if pid in seen:
                            continue
                        seen.add(pid)
                        candidates.append(r)
                        candidate_ids.append(pid)

                if not candidates:
                    continue

                async with self._uow_factory() as uow:
                    allowed_ids = await uow.quarantine.filter_not_quarantined(
                        lang=lang, pageids=candidate_ids
                    )

                if not allowed_ids:
                    continue

                for a in candidates:
                    if int(a.meta.pageid) not in allowed_ids:
                        continue
                    if len(pending) >= max_inflight:
                        break
                    _launch_embedding(a)

            while len(out) < n and pending:
                done, _ = await asyncio.wait(
                    set(pending.keys()), return_when=asyncio.FIRST_COMPLETED
                )
                _harvest_done(done_tasks=done)

            return out[:n]

        finally:
            if pending:
                for t in list(pending.keys()):
                    t.cancel()
                await asyncio.gather(*pending.keys(), return_exceptions=True)
                pending.clear()

    async def _maybe_await_embedding(self, article: Article) -> EmbeddingVector:
        res = self._model.get_embedding(article)
        if inspect.isawaitable(res):
            return await res
        return res
