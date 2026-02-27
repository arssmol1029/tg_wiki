import asyncio
import os
import signal
import grpc

from scpedia_protos.wiki.v1 import wiki_pb2, wiki_pb2_grpc

from wiki_service.service.http import HttpClient, HttpNotStartedError, HttpRequestError
from wiki_service.service.wiki_service import WikiService
from wiki_service.internal.langs import (
    normalize_lang,
    supported_langs_list,
    is_supported_lang,
    UnsupportedLanguage,
)
from wiki_service.internal.errors import map_http_error
from wiki_service.internal.to_pb import to_pb_meta, to_pb_article


class WikiGrpcServicer(wiki_pb2_grpc.WikiServiceServicer):
    def __init__(self, svc: WikiService) -> None:
        self._svc = svc

    async def GetRandomArticle(
        self, request: wiki_pb2.GetRandomArticleRequest, context
    ):
        if request.min_length <= 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "min_length must be > 0"
            )

        lang = normalize_lang(request.lang)
        if not is_supported_lang(lang):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        try:
            article = await self._svc.get_random_article(
                min_length=request.min_length or 0,
                lang=lang,
                text=request.text,
                image=request.image,
            )
        except HttpRequestError as e:
            await context.abort(map_http_error(e), str(e))
        except HttpNotStartedError as e:
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
        except UnsupportedLanguage:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        if article is None:
            return wiki_pb2.GetArticleResponse(found=False)

        return wiki_pb2.GetArticleResponse(article=to_pb_article(article), found=True)

    async def GetArticleByTitle(
        self, request: wiki_pb2.GetArticleByTitleRequest, context
    ):
        title = (request.title or "").strip()
        if not title:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "title is empty")

        lang = normalize_lang(request.lang)
        if not is_supported_lang(lang):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        try:
            article = await self._svc.get_article_by_title(
                title,
                lang=lang,
                text=request.text,
                image=request.image,
            )
        except HttpRequestError as e:
            await context.abort(map_http_error(e), str(e))
        except HttpNotStartedError as e:
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
        except UnsupportedLanguage:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        if article is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "article not found")

        return wiki_pb2.GetArticleResponse(article=to_pb_article(article), found=True)

    async def GetArticleByPageId(
        self, request: wiki_pb2.GetArticleByPageIdRequest, context
    ):
        if request.pageid <= 0:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "pageid must be > 0")

        lang = normalize_lang(request.lang)
        if not is_supported_lang(lang):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        try:
            article = await self._svc.get_article_by_pageid(
                int(request.pageid),
                lang=lang,
                text=request.text,
                image=request.image,
            )
        except HttpRequestError as e:
            await context.abort(map_http_error(e), str(e))
        except HttpNotStartedError as e:
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
        except UnsupportedLanguage:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        if article is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "article not found")

        return wiki_pb2.GetArticleResponse(article=to_pb_article(article), found=True)

    async def SearchArticles(self, request: wiki_pb2.SearchArticlesRequest, context):
        query = (request.query or "").strip()
        if not query:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "query is empty")

        limit = request.limit or 10
        if limit <= 0 or limit > 50:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "limit must be in 1..50"
            )

        lang = normalize_lang(request.lang)
        if not is_supported_lang(lang):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        try:
            items = await self._svc.search_articles(query, lang=lang, limit=limit)
        except HttpRequestError as e:
            await context.abort(map_http_error(e), str(e))
        except HttpNotStartedError as e:
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
        except UnsupportedLanguage:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        return wiki_pb2.SearchArticlesResponse(items=[to_pb_meta(m) for m in items])


async def serve() -> None:
    host = os.getenv("WIKI_GRPC_HOST", "0.0.0.0")
    port = int(os.getenv("WIKI_GRPC_PORT", "50051"))

    http = HttpClient()
    await http.start()

    svc = WikiService(http)

    server = grpc.aio.server(
        options=[
            ("grpc.max_send_message_length", 10 * 1024 * 1024),
            ("grpc.max_receive_message_length", 10 * 1024 * 1024),
        ]
    )
    wiki_pb2_grpc.add_WikiServiceServicer_to_server(WikiGrpcServicer(svc), server)

    server.add_insecure_port(f"{host}:{port}")
    await server.start()

    stop_evt = asyncio.Event()

    def _stop(*_args):
        stop_evt.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    await stop_evt.wait()
    await server.stop(grace=5)
    await http.close()
