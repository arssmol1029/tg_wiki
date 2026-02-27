import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {
                "query": {
                    "pages": {
                        "123": {
                            "pageid": 123,
                            "title": "T",
                            "fullurl": "U",
                            "extract": "hello",
                        }
                    }
                }
            },  # good test
            123,
        ),
        (
            {"query": [{"pageid": 123}]},
            None,  # incorrect structure
        ),
    ],
)
async def test_get_article_by_title(svc, monkeypatch, payload, expected):
    async def fake_fetch_by_title(http, titles, lang="ru", text=True, image=True):
        return payload

    monkeypatch.setattr(
        "wiki_service.service.wiki_client.fetch_by_title", fake_fetch_by_title
    )

    article = await svc.get_article_by_title("T", lang="ru", text=True, image=False)

    if expected is None:
        assert article is None
    else:
        assert article is not None
        assert article.meta.pageid == expected
        assert article.lang == "ru"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {
                "query": {
                    "pages": {
                        "123": {
                            "pageid": 123,
                            "title": "T",
                            "fullurl": "U",
                            "extract": "hello",
                        }
                    }
                }
            },
            123,
        ),  # good test
        (
            {
                "query": {
                    "pages": {
                        "123": {
                            "pageid": 123,
                            "title": "T",
                            "fullurl": "U",
                            "extract": "hello",
                            "missing": 1,
                        }
                    }
                }
            },  # have missing field
            None,
        ),
        (
            {
                "query": {
                    "pages": {
                        "123": {
                            "pageid": 123,
                            "fullurl": "U",
                            "extract": "hello",
                        }
                    }
                }
            },  # not have title field
            None,
        ),
    ],
)
async def test_get_article_by_pageid(svc, monkeypatch, payload, expected):
    async def fake_fetch_by_pageid(http, pageids, lang="ru", text=True, image=True):
        return payload

    monkeypatch.setattr(
        "wiki_service.service.wiki_client.fetch_by_pageid", fake_fetch_by_pageid
    )

    article = await svc.get_article_by_pageid(123, lang="ru", text=True, image=False)

    if expected is None:
        assert article is None
    else:
        assert article is not None
        assert article.meta.pageid == expected
        assert article.lang == "ru"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {
                "query": {
                    "pages": {
                        "123": {
                            "pageid": 123,
                            "title": "T",
                            "fullurl": "U",
                            "extract": "big_enough_hello",
                        }
                    }
                }
            },  # good test
            123,
        ),
        (
            {
                "query": {
                    "pages": {
                        "123": {
                            "pageid": 123,
                            "title": "T",
                            "fullurl": "U",
                            "extract": "small_hello",
                        }
                    }
                }
            },  # too small extract
            None,
        ),
    ],
)
async def test_get_random_article(svc, monkeypatch, payload, expected):
    async def fake_fetch_random(http, lang="ru", text=True, image=True):
        return payload

    monkeypatch.setattr(
        "wiki_service.service.wiki_client.fetch_random", fake_fetch_random
    )

    article = await svc.get_random_article(
        min_length=15, lang="ru", text=True, image=False
    )

    if expected is None:
        assert article is None
    else:
        assert article is not None
        assert article.meta.pageid == expected
        assert article.lang == "ru"
