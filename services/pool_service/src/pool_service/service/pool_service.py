from dataclasses import dataclass
from typing import Callable

from pool_service.service.pool_worker import PoolWorker
from pool_service.database.ports import Uow


@dataclass(frozen=True, slots=True)
class PoolServiceConfig:
    concurrency: int = 10
    max_attempts_multiplier: int = 5
    max_inflight: int = 50
    min_inflight: int = 20


class PoolService:
    def __init__(
        self,
        *,
        worker: PoolWorker,
        uow_factory: Callable[[], Uow],
        cfg: PoolServiceConfig | None = None,
    ):
        self._worker = worker
        self._uow_factory = uow_factory
        self._cfg = cfg or PoolServiceConfig()
