from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from tg_wiki.db.config import DBConfig


def create_engine(cfg: DBConfig) -> AsyncEngine:
    return create_async_engine(
        cfg.dsn,
        pool_size=cfg.pool_size,
        max_overflow=cfg.max_overflow,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
