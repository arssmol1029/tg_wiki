from wiki_service.service.http import HttpClient, Json
from wiki_service.internal.map_api_lang import map_api_lang


IMAGE_WIDTH = 300


async def fetch_random(
    http: HttpClient, lang: str = "ru", text: bool = True, image: bool = True
) -> Json:
    """
    Fetches a random article from the Ru Wikipedia.

    Args:
        http: The HttpClient instance to use for making requests.

    Returns:
        A Json containing the article's information.
    """
    props = ["info"]
    if text:
        props.append("extracts")
    if image:
        props.append("pageimages")

    params = {
        "action": "query",
        "format": "json",
        "generator": "random",
        "grnlimit": 1,
        "grnnamespace": 0,
        "prop": "|".join(props),
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "pithumbsize": IMAGE_WIDTH,
    }

    return await http.get_json(map_api_lang(lang), params=params)


async def fetch_by_title(
    http: HttpClient,
    titles: list[str],
    lang: str = "ru",
    text: bool = True,
    image: bool = True,
) -> Json:
    """
    Fetches an article by its title from the Ru Wikipedia.

    Args:
        http: The HttpClient instance to use for making requests.
        titles: The list of titles of the articles to fetch.

    Returns:
        A Json containing the article's information.
    """
    props = ["info"]
    if text:
        props.append("extracts")
    if image:
        props.append("pageimages")

    params = {
        "action": "query",
        "format": "json",
        "titles": "|".join(titles),
        "prop": "|".join(props),
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "pithumbsize": IMAGE_WIDTH,
    }

    return await http.get_json(map_api_lang(lang), params=params)


async def fetch_by_pageid(
    http: HttpClient,
    pageid: list[str],
    lang: str = "ru",
    text: bool = True,
    image: bool = True,
) -> Json:
    """
    Fetches an article by its pageid from the Ru Wikipedia.

    Args:
        http: The HttpClient instance to use for making requests.
        pageid: The pageid of the article to fetch.

    Returns:
        A Json containing the article's information.
    """
    props = ["info"]
    if text:
        props.append("extracts")
    if image:
        props.append("pageimages")

    params = {
        "action": "query",
        "format": "json",
        "pageids": "|".join(pageid),
        "prop": "|".join(props),
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "pithumbsize": IMAGE_WIDTH,
    }

    return await http.get_json(map_api_lang(lang), params=params)


async def search_by_title(
    http: HttpClient, query: str, lang: str = "ru", limit: int = 5
) -> Json:
    """
    Searches for articles by matching in the title of article on the Ru Wikipedia.

    Args:
        http: The HttpClient instance to use for making requests.
        query: The query to search for.
        limit: The maximum number of search results to return.

    Returns:
        A Json containing the search results.
    """
    params = {
        "action": "opensearch",
        "search": query,
        "limit": limit,
        "namespace": 0,
        "format": "json",
    }

    return await http.get_json(map_api_lang(lang), params=params)


async def search_by_text(
    http: HttpClient, query: str, lang: str = "ru", limit: int = 5
) -> Json:
    """
    Searches for articles by matching in the text of article on the Ru Wikipedia.

    Args:
        http: The HttpClient instance to use for making requests.
        query: The query to search for.
        limit: The maximum number of search results to return.

    Returns:
        A Json containing the search results.
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "info",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "srnamespace": 0,
    }

    return await http.get_json(map_api_lang(lang), params=params)
