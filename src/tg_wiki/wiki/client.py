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


async def opensearch(query: str, limit: int = 5) -> list[str]:
    '''
    Searches for articles by query on the Ru Wikipedia.
    
    Args:
        query: The query to search for.

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

    return list(filter(lambda title: title.strip() != "", titles))


async def search_by_text(query: str, limit: int = 5) -> list[str]:
    '''
    Searches for articles by text on the Ru Wikipedia.
    
    Args:
        query: The text to search for.

    Returns:
        A list of article titles that match the search text.
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
    titles = [result.get("title", "") for result in results if "title" in result]

    return list(filter(lambda title: title.strip() != "", titles))
