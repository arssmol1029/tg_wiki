from typing import Optional
from webbrowser import get

from tg_wiki.clients.http import HttpClient, Json


RUWIKI_API = "https://ru.wikipedia.org/w/api.php"
IMAGE_WIDTH = 300


async def fetch_random(http: HttpClient) -> Json:
    '''
    Fetches a random article from the Ru Wikipedia.

    Args:
        http: The HttpClient instance to use for making requests.
    
    Returns:
        A dictionary containing the article's information, or None if no article was found.
    '''
    params = {
        "action": "query",
        "format": "json",
        "generator": "random",
        "grnlimit": 1,
        "grnnamespace": 0,
        "prop": "extracts|info|pageimages",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "pithumbsize": IMAGE_WIDTH,
    }
    # data = await http.get_json(RUWIKI_API, params=params)
    # if not isinstance(data, dict):
    #     return None
    # pages = data.get("query", {}).get("pages", {})
    # if not pages:
    #     return None
    
    return await http.get_json(RUWIKI_API, params=params)


async def fetch_by_title(http: HttpClient, titles: list[str]) -> Json:
    '''
    Fetches an article by its title from the Ru Wikipedia.
    
    Args:
        http: The HttpClient instance to use for making requests.
        titles: The list of titles of the articles to fetch.

    Returns:
        A dictionary containing the article's information, or None if no article was found.
    '''
    params = {
        "action": "query",
        "format": "json",
        "titles": "|".join(titles),
        "prop": "extracts|info|pageimages",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "pithumbsize": IMAGE_WIDTH,
    }
    # data = await http.get_json(RUWIKI_API, params=params)
    # if not isinstance(data, dict):
    #     return None
    # pages = data.get("query", {}).get("pages", {})
    # if not pages:
    #     return None
    
    return await http.get_json(RUWIKI_API, params=params)


async def fetch_by_pageid(http: HttpClient, pageid: str) -> Json:
    '''
    Fetches an article by its pageid from the Ru Wikipedia.
    
    Args:
        http: The HttpClient instance to use for making requests.
        pageid: The pageid of the article to fetch.

    Returns:
        A dictionary containing the article's information, or None if no article was found.
    '''
    params = {
        "action": "query",
        "format": "json",
        "pageids": pageid,
        "prop": "extracts|info|pageimages",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "pithumbsize": IMAGE_WIDTH,
    }
    # data = await http.get_json(RUWIKI_API, params=params)
    # if not isinstance(data, dict):
    #     return None
    # pages = data.get("query", {}).get("pages", {})
    # if not pages:
    #     return None
    
    return await http.get_json(RUWIKI_API, params=params)


async def search_by_title(http: HttpClient, query: str, limit: int = 5) -> Json:
    '''
    Searches for articles by matching in the title of article on the Ru Wikipedia.
    
    Args:
        http: The HttpClient instance to use for making requests.
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

    # data = await http.get_json(RUWIKI_API, params=params)
    # if not data or not isinstance(data, list) or len(data) < 2:
    #     return []
    # titles = data[1]

    return await http.get_json(RUWIKI_API, params=params)


async def search_by_text(http: HttpClient, query: str, limit: int = 5) -> Json:
    '''
    Searches for articles by matching in the text of article on the Ru Wikipedia.
    
    Args:
        http: The HttpClient instance to use for making requests.
        query: The query to search for.
        limit: The maximum number of search results to return.

    Returns:
        A list of dictionaries containing the title and pageid of the found articles.
    '''
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "srnamespace": 0,
    }

    # data = await http.get_json(RUWIKI_API, params=params)
    # if not isinstance(data, dict):
    #     return []
    
    # results = data.get("query", {}).get("search", [])

    return await http.get_json(RUWIKI_API, params=params)
