from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class DBConfig:
    dsn: str
    pool_size: int = 5
    max_overflow: int = 5
    pref_vector_dim: int = 1536

    @staticmethod
    def from_env(*, prefix: str = "") -> "DBConfig":
        dsn = os.getenv(f"{prefix}DB_DSN", "").strip()
        if not dsn:
            raise ValueError("DB_DSN is required to enable the database")

        def _get_int(name: str, default: int) -> int:
            raw = os.getenv(f"{prefix}{name}")
            if raw is None or not raw.strip():
                return default
            try:
                return int(raw)
            except ValueError as e:
                raise ValueError(f"{name} must be an int, got: {raw!r}") from e

        return DBConfig(
            dsn=dsn,
            pool_size=_get_int("DB_POOL_SIZE", 5),
            max_overflow=_get_int("DB_MAX_OVERFLOW", 5),
            pref_vector_dim=_get_int("PREF_VECTOR_DIM", 1536),
        )
