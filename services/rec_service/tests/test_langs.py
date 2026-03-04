import importlib
import pytest


def _reload_langs():
    import rec_service.internal.langs as langs

    return importlib.reload(langs)


def test_langs_requires_init():
    langs = _reload_langs()

    with pytest.raises(RuntimeError):
        langs.supported_langs_list()

    with pytest.raises(RuntimeError):
        langs.is_supported_lang("ru")

    with pytest.raises(RuntimeError):
        langs.pool_size_per_lang()

    with pytest.raises(RuntimeError):
        langs.extra_size_per_lang()


def test_init_langs_and_accessors(tmp_path):
    langs = _reload_langs()

    csv = tmp_path / "langs.csv"
    csv.write_text(
        """# comment line\nlang,pool_size,extra_size\nru,10,5\n EN , 3 , 2\n""",
        encoding="utf-8",
    )

    langs.init_langs(csv_path=csv)

    assert langs.normalize_lang(" RU ") == "ru"
    assert langs.is_supported_lang("ru") is True
    assert langs.is_supported_lang("en") is True
    assert langs.is_supported_lang("xx") is False

    assert langs.supported_langs_list() == ("en", "ru")
    assert langs.pool_size_per_lang() == {"ru": 10, "en": 3}
    assert langs.extra_size_per_lang() == {"ru": 5, "en": 2}


@pytest.mark.parametrize(
    "body",
    [
        "",  # empty file
        "lang,pool_size\nru,1",  # missing columns
        "lang,pool_size,extra_size\n,1,1",  # empty lang
        "lang,pool_size,extra_size\nru,0,1",  # invalid pool_size
        "lang,pool_size,extra_size\nru,1,0",  # invalid extra_size
        "lang,pool_size,extra_size\nru,foo,1",  # non-int pool_size
        "lang,pool_size,extra_size\nru,1,bar",  # non-int extra_size
        "lang,pool_size,extra_size\nru,1,1\nRU,2,2",  # duplicate after normalize
    ],
)
def test_init_langs_invalid_csv(tmp_path, body):
    langs = _reload_langs()

    csv = tmp_path / "langs.csv"
    csv.write_text(body, encoding="utf-8")

    with pytest.raises((ValueError, FileNotFoundError)):
        langs.init_langs(csv_path=csv)
