import json

from typing import Any

from tg_wiki.domain.article import Article, ArticleMeta


def dumps_article(article: Article) -> str:
    payload = {
        "meta": {
            "pageid": article.meta.pageid,
            "title": article.meta.title,
            "url": article.meta.url,
            "thumbnail_url": article.meta.thumbnail_url,
        },
        "extract": article.extract,
        "lang": article.lang,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def loads_article(raw: str) -> Article:
    data: dict[str, Any] = json.loads(raw)
    meta = data["meta"]
    return Article(
        meta=ArticleMeta(
            pageid=int(meta["pageid"]),
            title=str(meta.get("title", "")),
            url=str(meta.get("url", "")),
            thumbnail_url=meta.get("thumbnail_url"),
        ),
        extract=data.get("extract"),
        lang=str(data.get("lang", "ru")),
    )
