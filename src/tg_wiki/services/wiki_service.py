from typing import Optional

from tg_wiki.wiki.client import fetch_random_article_raw
from tg_wiki.wiki.client import fetch_article_by_title_raw



async def is_valid_article(article: dict, min_length: int = 0) -> bool:
    '''
    Filters the raw article data
    
    Args:
        article: The raw data of the article as returned by the Wikipedia API.

    Returns:
        True if the article is valid and contains enough information, False otherwise.
    '''
    if article.get("missing") is not None:
        return False
    if article.get("title") is None:
        return False
    extract = article.get("extract", None)
    if not extract:
        return False
    return len(extract.strip()) >= min_length


async def get_next_article(min_length: int = 100) -> Optional[dict]:
    '''
    Fetches a random article from the Ru Wikipedia and checks if it's valid.
    
    Returns:
        A dictionary containing the article's information.
    '''
    while True:
        article = await fetch_random_article_raw()
        if article:
            if await is_valid_article(article, min_length=min_length):
                return article


async def get_article_by_title(title: str) -> Optional[dict]:
    '''
    Fetches an article by its title from the Ru Wikipedia and checks if it's valid.
    
    Args:
        title: The title of the article to fetch.

    Returns:
        A dictionary containing the article's information, or None if no valid article was found.
    '''
    article = await fetch_article_by_title_raw(title)
    if article and await is_valid_article(article):
        return article