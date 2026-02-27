import pytest

from wiki_service.internal.langs import (
    normalize_lang,
    is_supported_lang,
    map_api_lang,
    UnsupportedLanguage,
)


def test_normalize_lang():
    assert normalize_lang("ru  ") == "ru"
    assert normalize_lang(" RU ") == "ru"
    assert normalize_lang("") == ""


def test_supported_langs():
    assert is_supported_lang("ru")
    assert not is_supported_lang("xx")


def test_map_api_lang_unsupported():
    with pytest.raises(UnsupportedLanguage):
        map_api_lang("xx")
