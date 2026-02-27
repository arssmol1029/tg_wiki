from typing import Final

SUPPORTED_LANGS: Final[dict[str, str]] = {
    "ru": "https://ru.wikipedia.org/w/api.php",
    "en": "https://en.wikipedia.org/w/api.php",
}


class UnsupportedLanguage(ValueError):
    """Language not supported"""


def normalize_lang(lang: str) -> str:
    lang = (lang or "").strip().lower()
    return lang


def map_api_lang(lang: str) -> str:
    lang = normalize_lang(lang)
    api = SUPPORTED_LANGS.get(lang)
    if api is None:
        raise UnsupportedLanguage(lang)
    return api


def supported_langs_list() -> list[str]:
    return list(SUPPORTED_LANGS)


def is_supported_lang(lang: str) -> bool:
    return normalize_lang(lang) in SUPPORTED_LANGS
