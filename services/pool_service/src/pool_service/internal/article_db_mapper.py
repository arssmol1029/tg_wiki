from pool_service.domain.article import Article, ArticleMeta
from pool_service.database.ports import ArticleRow, ArticleUpsert


def to_domain_article(row: ArticleRow) -> Article:
    meta = ArticleMeta(
        pageid=row.pageid,
        title=row.title,
        url=row.url,
        thumbnail_url=row.thumbnail_url or None,
    )
    return Article(meta=meta, extract=row.extract or None, lang=row.lang)


def from_domain_article(article: Article) -> ArticleUpsert:
    return ArticleUpsert(
        pageid=article.meta.pageid,
        lang=article.lang,
        url=article.meta.url,
        title=article.meta.title,
        thumbnail_url=article.meta.thumbnail_url,
        extract=article.extract,
        extract_len=len(article.extract) if article.extract else None,
    )
