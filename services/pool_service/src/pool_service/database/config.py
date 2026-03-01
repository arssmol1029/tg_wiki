import os

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DBConfig:
    dsn: str

    pool_size: int = 5
    max_overflow: int = 5

    pool_timeout: int = 30
    pool_recycle: int = 1800

    echo: bool = False

    @staticmethod
    def from_env(*, prefix: str = "DB") -> "DBConfig":
        dsn = os.getenv(f"{prefix}_DSN", "").strip()
        if not dsn:
            raise ValueError("DSN is required to enable the database")

        def _get_int(name: str, default: int) -> int:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None or not raw.strip():
                return default
            try:
                return int(raw)
            except ValueError as e:
                raise ValueError(f"{name} must be an int, got: {raw!r}") from e

        def _get_bool(name: str, default: bool) -> bool:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None:
                return default
            s = raw.strip().lower()
            if s in ("1", "true", "yes", "y", "on"):
                return True
            if s in ("0", "false", "no", "n", "off", ""):
                return False
            raise ValueError(f"{name} must be a boolean-like string, got: {raw!r}")

        return DBConfig(
            dsn=dsn,
            pool_size=_get_int("POOL_SIZE", 5),
            max_overflow=_get_int("MAX_OVERFLOW", 5),
            pool_timeout=_get_int("POOL_TIMEOUT", 30),
            pool_recycle=_get_int("POOL_RECYCLE", 1800),
            echo=_get_bool("ECHO", False),
        )
