import csv
from dataclasses import dataclass
from pathlib import Path


def read_langs_csv(
    path: str | Path, pool_sizes: dict[str, int], extra_sizes: dict[str, int]
):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"langs.csv not found: {p}")

    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(
            (line for line in f if line.strip() and not line.lstrip().startswith("#"))
        )

        if (
            not reader.fieldnames
            or "lang" not in reader.fieldnames
            or "pool_size" not in reader.fieldnames
            or "extra_size" not in reader.fieldnames
        ):
            raise ValueError(
                "langs.csv must have header with columns: lang,pool_size,extra_size"
            )

        for row in reader:
            lang = normalize_lang(row.get("lang") or "")
            raw_pool_size = (row.get("pool_size") or "").strip()
            raw_extra_size = (row.get("extra_size") or "").strip()

            if not lang:
                raise ValueError(f"langs.csv: empty lang in row: {row}")

            try:
                pool_size = int(raw_pool_size)
            except ValueError as e:
                raise ValueError(
                    f"langs.csv: pool_size must be int for lang={lang!r}, got {raw_pool_size!r}"
                ) from e

            try:
                extra_size = int(raw_extra_size)
            except ValueError as e:
                raise ValueError(
                    f"langs.csv: extra_size must be int for lang={lang!r}, got {raw_extra_size!r}"
                ) from e

            if pool_size <= 0:
                raise ValueError(
                    f"langs.csv: pool_size must be > 0 for lang={lang!r}, got {pool_size}"
                )

            if extra_size <= 0:
                raise ValueError(
                    f"langs.csv: extra_size must be > 0 for lang={lang!r}, got {extra_size}"
                )

            if (lang in pool_sizes) or (lang in extra_sizes):
                raise ValueError(f"langs.csv: duplicate lang {lang!r}")

            pool_sizes[lang] = int(pool_size)
            extra_sizes[lang] = int(extra_size)


_SUPPORTED_LANGS: list[str] = []
_POOL_SIZES: dict[str, int] = {}
_EXTRA_SIZES: dict[str, int] = {}
_INITIALIZED: bool = False


def init_langs(*, csv_path: str | Path) -> None:
    global _SUPPORTED_LANGS, _INITIALIZED
    if _INITIALIZED:
        return
    read_langs_csv(csv_path, _POOL_SIZES, _EXTRA_SIZES)

    _SUPPORTED_LANGS = sorted(_POOL_SIZES.keys())
    _INITIALIZED = True


def normalize_lang(lang: str) -> str:
    lang = (lang or "").strip().lower()
    return lang


def supported_langs_list() -> tuple[str, ...]:
    if not _INITIALIZED:
        raise RuntimeError(
            "langs not initialized. Call init_langs(csv_path=...) on startup"
        )
    return tuple(_SUPPORTED_LANGS)


def is_supported_lang(lang: str) -> bool:
    if not _INITIALIZED:
        raise RuntimeError(
            "langs not initialized. Call init_langs(csv_path=...) on startup"
        )
    return normalize_lang(lang) in _POOL_SIZES


def pool_size_per_lang() -> dict[str, int]:
    if not _INITIALIZED:
        raise RuntimeError(
            "langs not initialized. Call init_langs(csv_path=...) on startup"
        )
    return dict(_POOL_SIZES)


def extra_size_per_lang() -> dict[str, int]:
    if not _INITIALIZED:
        raise RuntimeError(
            "langs not initialized. Call init_langs(csv_path=...) on startup"
        )
    return dict(_EXTRA_SIZES)
