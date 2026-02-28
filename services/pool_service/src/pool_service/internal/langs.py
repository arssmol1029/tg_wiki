from typing import Final

SUPPORTED_LANGS: Final[list[str]] = ["ru", "en"]


def normalize_lang(lang: str) -> str:
    lang = (lang or "").strip().lower()
    return lang


def supported_langs_list() -> list[str]:
    return SUPPORTED_LANGS


def is_supported_lang(lang: str) -> bool:
    return normalize_lang(lang) in SUPPORTED_LANGS
