import logging
import os
import sys
from typing import Final


def _level_from_env(var: str, default: str = "INFO") -> int:
    raw = os.getenv(var, default).strip().upper()
    return getattr(logging, raw, logging.INFO)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "component"):
            record.component = "app"
        return True


def setup_logging() -> None:
    root = logging.getLogger()

    if getattr(root, "_rec_service_logging_configured", False):
        return

    level = _level_from_env("LOG_LEVEL", "INFO")
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)

    fmt: Final[str] = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s %(levelname)s %(name)s [%(component)s] %(message)s",
    )
    datefmt: Final[str] = os.getenv("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handler.addFilter(_ContextFilter())

    root.handlers.clear()
    root.addHandler(handler)

    root._rec_service_logging_configured = True  # type: ignore[attr-defined]


def get_logger(name: str, *, component: str) -> logging.LoggerAdapter:
    base = logging.getLogger(name)
    return logging.LoggerAdapter(base, {"component": component})
