from typing import Optional

import tg_wiki.wiki.client as wiki


MAX_ATTEMPTS = 10


def is_valid_article(article: dict, min_length: int = 0, max_length: int = 10000) -> bool:
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
    for _ in range(MAX_ATTEMPTS):
        article = await wiki.fetch_random()
        if article:
            if is_valid_article(article, min_length=min_length):
                return article


async def get_article_by_title(title: str) -> Optional[dict]:
    '''
    Fetches an article by its title from the Ru Wikipedia and checks if it's valid.
    
    Args:
        title: The title of the article to fetch.

    Returns:
        A dictionary containing the article's information, or None if no valid article was found.
    '''
    article = await wiki.fetch_by_title(title)
    if article and is_valid_article(article):
        return article
    

async def get_article_by_pageid(pageid: str) -> Optional[dict]:
    '''
    Fetches an article by its pageid from the Ru Wikipedia and checks if it's valid.
    
    Args:
        pageid: The pageid of the article to fetch.

    Returns:
        A dictionary containing the article's information, or None if no valid article was found.
    '''
    article = await wiki.fetch_by_pageid(pageid)
    if article and is_valid_article(article):
        return article
    

async def search_articles(query: str, limit: int = 5) -> list[dict[str, str]]:
    '''
    Searches for articles by query on the Ru Wikipedia.
    
    Args:
        query: The query to search for.

    Returns:
        A list of dictionaries containing the title and URL of the found articles.
    '''
    results_title = await wiki.opensearch(query, limit=limit)
    
    if len(results_title) < limit:
        results_text = await wiki.search_by_text(query, limit=limit - len(results_title))
        results_title.extend(results_text)

    return results_title