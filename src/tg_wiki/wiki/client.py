from typing import Optional

from tg_wiki.clients.http import get


RUWIKI_API = "https://ru.wikipedia.org/w/api.php"


async def fetch_random() -> Optional[dict]:
    '''
    Fetches a random article from the Ru Wikipedia.
    
    Returns:
        A dictionary containing the article's information, or None if no article was found.
    '''
    params = {
        "action": "query",
        "format": "json",
        "generator": "random",
        "grnlimit": 1,
        "grnnamespace": 0,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
    }
    data = await get(RUWIKI_API, params=params)
    if not isinstance(data, dict):
        return None
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None
    
    return next(iter(pages.values()))


async def fetch_by_title(title: str) -> Optional[dict]:
    '''
    Fetches an article by its title from the Ru Wikipedia.
    
    Args:
        title: The title of the article to fetch.

    Returns:
        A dictionary containing the article's information, or None if no article was found.
    '''
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
    }
    data = await get(RUWIKI_API, params=params)
    if not isinstance(data, dict):
        return None
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None
    
    return next(iter(pages.values()))


async def fetch_by_pageid(pageid: str) -> Optional[dict]:
    '''
    Fetches an article by its pageid from the Ru Wikipedia.
    
    Args:
        pageid: The pageid of the article to fetch.

    Returns:
        A dictionary containing the article's information, or None if no article was found.
    '''
    params = {
        "action": "query",
        "format": "json",
        "pageids": pageid,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
    }
    data = await get(RUWIKI_API, params=params)
    if not isinstance(data, dict):
        return None
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None
    
    return next(iter(pages.values()))


async def opensearch_titles(query: str, limit: int = 5) -> list[str]:
    '''
    Searches for articles by matching in the title of article on the Ru Wikipedia.
    
    Args:
        query: The query to search for.
        limit: The maximum number of search results to return.

    Returns:
        A list of article titles that match the search query.
    '''
    params = {
        "action": "opensearch",
        "search": query,
        "limit": limit,
        "namespace": 0,
        "format": "json",
    }

    data = await get(RUWIKI_API, params=params)
    if not data:
        return []
    titles = data[1]

    return titles


async def opensearch(query: str, limit: int = 5) -> list[dict[str, str]]:
    '''
    Searches for articles by matching in the title of article on the Ru Wikipedia, returning titles and pageids.
    
    Args:
        query: The query to search for.
        limit: The maximum number of search results to return.

    Returns:
        A list of dictionaries containing the title and pageid of the found articles.
    '''
    params = {
        "action": "opensearch",
        "search": query,
        "limit": limit,
        "namespace": 0,
        "format": "json",
    }

    data = await get(RUWIKI_API, params=params)
    if not data:
        return []
    
    titles = data[1]
    pageids = []

    for title in titles:
        result = await fetch_by_title(title)
        if result:
            pageids.append(result.get("pageid", ""))
        else:
            pageids.append("")

    return [{"title": title, "pageid": pageid} for title, pageid in zip(titles, pageids)]


async def search_by_text(query: str, limit: int = 5) -> list[dict[str, str]]:
    '''
    Searches for articles by matching in the text of article on the Ru Wikipedia.
    
    Args:
        query: The query to search for.
        limit: The maximum number of search results to return.

    Returns:
        A list of article titles that match the search query.
    '''
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "srnamespace": 0,
    }

    data = await get(RUWIKI_API, params=params)
    if not isinstance(data, dict):
        return []
    
    results = data.get("query", {}).get("search", [])

    return [{"title": result.get("title", ""), "pageid": result.get("pageid", "")} for result in results]
