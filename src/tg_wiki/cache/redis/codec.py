import json

from typing import Any

from tg_wiki.domain.article import Article, ArticleMeta
from tg_wiki.domain.user import UserSettings


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
            thumbnail_url=str(meta.get("thumbnail_url")),
        ),
        extract=data.get("extract"),
        lang=str(data.get("lang", "ru")),
    )


def dumps_settings(settings: UserSettings) -> str:
    payload = {
        "page_len": settings.page_len,
        "send_text": settings.send_text,
        "send_image": settings.send_image,
        "app_lang": settings.app_lang,
        "wiki_lang": settings.wiki_lang,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def loads_settings(raw: str) -> UserSettings:
    data: dict[str, Any] = json.loads(raw)
    return UserSettings(
        page_len=int(data["page_len"]),
        send_text=bool(data["send_text"]),
        send_image=bool(data["send_image"]),
        app_lang=str(data["app_lang"]),
        wiki_lang=str(data["wiki_lang"]),
    )
