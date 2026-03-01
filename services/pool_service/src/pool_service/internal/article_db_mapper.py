from pool_service.domain.article import Article
from pool_service.domain.embedding import EmbeddingVector, EMBEDDING_DIM
from pool_service.database.ports import ArticleRow, ArticleInsert


def from_article_row(row: ArticleRow) -> Article:
    return Article(
        pageid=int(row.pageid),
        title=str(row.title),
        url=str(row.url),
        lang=str(row.lang),
        thumbnail_url=row.thumbnail_url or None,
        extract=row.extract or None,
    )


def article_to_insert(
    article: Article, *, embedding: EmbeddingVector | list[float]
) -> ArticleInsert:
    if isinstance(embedding, EmbeddingVector):
        embedding = embedding.data

    extract = article.extract or ""

    return ArticleInsert(
        pageid=int(article.pageid),
        title=str(article.title),
        url=str(article.url),
        thumbnail_url=str(article.thumbnail_url or ""),
        extract=str(extract),
        extract_len=len(extract),
        embedding=list(map(float, embedding)),
    )
