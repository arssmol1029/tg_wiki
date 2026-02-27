import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title_payload, text_payload, pages_payload, limit, expected_titles",
    [
        (
            ["q", ["A", "B", "C"], [], []],  # opensearch: ["A","B","C"]
            {"query": {"search": []}},  # should not be used
            {
                "query": {
                    "pages": {
                        "1": {"pageid": 1, "title": "A", "fullurl": "UA"},
                        "2": {"pageid": 2, "title": "B", "fullurl": "UB"},
                        "3": {"pageid": 3, "title": "C", "fullurl": "UC"},
                    }
                }
            },
            3,
            {"A", "B", "C"},
        ),
        (
            ["q", ["A"], [], []],  # opensearch: ["A"]
            {"query": {"search": [{"title": "B"}, {"title": "C"}]}},
            {
                "query": {
                    "pages": {
                        "1": {"pageid": 1, "title": "A", "fullurl": "UA"},
                        "2": {"pageid": 2, "title": "B", "fullurl": "UB"},
                        "3": {"pageid": 3, "title": "C", "fullurl": "UC"},
                    }
                }
            },
            3,
            {"A", "B", "C"},
        ),
        (
            ["q", ["", "   ", None, "A", "A"], [], []],  # duplicates and empty titles
            {"query": {"search": [{"title": ""}, {"title": "B"}]}},
            {
                "query": {
                    "pages": {
                        "1": {"pageid": 1, "title": "A", "fullurl": "UA"},
                        "2": {
                            "pageid": 2,
                            "title": "B",
                            "fullurl": "UB",
                            "missing": 1,
                        },  # should be filtered
                        "3": {
                            "pageid": 3,
                            "title": "",
                            "fullurl": "UC",
                        },  # should be filtered
                    }
                }
            },
            2,
            {"A"},
        ),
        (
            ["q", [], [], []],
            {"query": {"search": []}},
            {"query": {"pages": {}}},
            5,
            set(),
        ),  # nothing was found
    ],
)
async def test_search_articles(
    svc,
    monkeypatch,
    title_payload,
    text_payload,
    pages_payload,
    limit,
    expected_titles,
):
    async def fake_search_by_title(http, query, lang="ru", limit=5):
        return title_payload

    async def fake_search_by_text(http, query, lang="ru", limit=5):
        return text_payload

    async def fake_fetch_by_title(http, titles, lang="ru", text=True, image=True):
        assert lang == "ru"
        assert text is False
        return pages_payload

    monkeypatch.setattr(
        "wiki_service.service.wiki_client.search_by_title", fake_search_by_title
    )
    monkeypatch.setattr(
        "wiki_service.service.wiki_client.search_by_text", fake_search_by_text
    )
    monkeypatch.setattr(
        "wiki_service.service.wiki_client.fetch_by_title", fake_fetch_by_title
    )

    res = await svc.search_articles("q", lang="ru", limit=limit)

    assert isinstance(res, list)

    got_titles = {m.title for m in res}
    assert got_titles == expected_titles

    for m in res:
        assert m.pageid > 0
        assert m.title.strip()
        assert m.url is not None and m.url.strip()
