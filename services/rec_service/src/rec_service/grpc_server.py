import asyncio
import os
import signal
import grpc

from scpedia_protos.rec.v1 import rec_pb2, rec_pb2_grpc

from rec_service.database.config import DBConfig
from rec_service.database.postgres.postgres import make_uow_factory
from rec_service.database.session import create_sessionmaker, create_engine
from rec_service.pool.pool_service import PoolService
from rec_service.rec.rec_service import RecService, RecServiceConfig
from rec_service.internal.langs import (
    init_langs,
    normalize_lang,
    supported_langs_list,
    is_supported_lang,
)
from rec_service.domain.vector import is_valid_vector
from rec_service.internal.article_grpc_mapper import to_rec_pb_article
from rec_service.internal.logging import setup_logging, get_logger


log = get_logger(__name__, component="grpc")


class RecGrpcServicer(rec_pb2_grpc.RecServiceServicer):
    def __init__(
        self, rec_service: RecService, pool_service: PoolService, max_count: int = 16
    ) -> None:
        self._rec_service = rec_service
        self._pool_service = pool_service
        self._max_count = max_count

    async def GetArticle(self, request: rec_pb2.GetArticleRequest, context):
        user_id = request.userid

        lang = normalize_lang(request.lang)
        if not is_supported_lang(lang):
            log.warning(
                "Language is not supported",
                extra={
                    "method": "GetArticle",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INVALID_ARGUMENT_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        min_length = request.min_length or 0
        if min_length < 0:
            log.warning(
                "min_length must be >= 0",
                extra={
                    "method": "GetArticle",
                    "user_id": user_id,
                    "lang": lang,
                    "min_length": min_length,
                    "status": "INVALID_ARGUMENT_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "min_length must be >= 0"
            )

        count = min(max(1, request.count), self._max_count)

        pref = await self._rec_service.get_user_pref(user_id=user_id)
        if not pref or not is_valid_vector(pref):
            log.error(
                "Cant load user preference",
                extra={
                    "method": "GetArticle",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INTERNAL_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"cant load user preference",
            )
            return

        articles = await self._pool_service.get_best_articles(
            lang=lang, pref=pref.data, count=count, min_length=min_length
        )
        text = request.text
        image = request.image

        log.info(
            "Recieved %d, get %d articles",
            count,
            len(articles),
            extra={
                "method": "GetArticle",
                "user_id": user_id,
                "lang": lang,
                "status": "OK",
            },
        )

        return rec_pb2.GetArticleResponse(
            articles=[
                to_rec_pb_article(article=article, text=text, image=image)
                for article in articles
            ]
        )

    async def UpdatePreference(self, request: rec_pb2.UpdatePreferenceRequest, context):
        user_id = request.userid
        reaction = request.reaction
        pageid = request.pageid

        lang = normalize_lang(request.lang)
        if not is_supported_lang(lang):
            log.warning(
                "Language is not supported",
                extra={
                    "method": "UpdatePreference",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INVALID_ARGUMENT_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"language is not supported, try {', '.join(supported_langs_list())}",
            )

        pref = await self._rec_service.get_user_pref(user_id=user_id)
        if not pref or not is_valid_vector(pref):
            log.error(
                "Cant load user preference",
                extra={
                    "method": "UpdatePreference",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INTERNAL_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"cant load user preference",
            )
            return

        embedding = await self._pool_service.get_article_embedding(
            lang=lang, pageid=pageid
        )
        if not embedding or not is_valid_vector(embedding):
            log.error(
                "Cant load article embedding",
                extra={
                    "method": "UpdatePreference",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INTERNAL_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"cant load article embedding",
            )
            return

        calibration_size = await self._rec_service.get_user_calibration_size(
            user_id=user_id
        )
        if calibration_size is None:
            log.error(
                "Cant load user calibration_size",
                extra={
                    "method": "UpdatePreference",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INTERNAL_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"cant load user",
            )
            return

        total_seen = await self._rec_service.get_user_total_seen(user_id=user_id)
        if total_seen is None:
            log.error(
                "Cant load user total_seen",
                extra={
                    "method": "UpdatePreference",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INTERNAL_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"cant load user",
            )
            return

        pref = pref.update(
            reaction=reaction,
            embedding=embedding,
            total_seen=total_seen,
            calibration=(calibration_size != 0),
        )

        success = await self._rec_service.update_user_pref(user_id=user_id, pref=pref)
        if not success:
            log.error(
                "Cant store user preference",
                extra={
                    "method": "UpdatePreference",
                    "user_id": user_id,
                    "lang": lang,
                    "status": "INTERNAL_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"cant store user preference",
            )
            return

        log.info(
            "Updated user preference",
            extra={
                "method": "UpdatePreference",
                "user_id": user_id,
                "lang": lang,
                "status": "OK",
            },
        )

        return rec_pb2.UpdatePreferenceResponse(success=success)

    async def CreateUser(self, request: rec_pb2.UpsertUserRequest, context):
        user_id = request.userid

        calibration_size = request.calibration_size
        if calibration_size is not None and calibration_size < 0:
            log.warning(
                "calibration_size must be >= 0",
                extra={
                    "method": "CreateUser",
                    "user_id": user_id,
                    "calibration_size": calibration_size,
                    "status": "INVALID_ARGUMENT_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "calibration_size must be >= 0"
            )

        success = await self._rec_service.create_user(
            user_id=user_id, calibration_size=calibration_size
        )

        log.info(
            "Created user",
            extra={
                "method": "CreateUser",
                "user_id": user_id,
                "status": "OK",
            },
        )

        return rec_pb2.CreateUserResponse(success=success)

    async def ResetUser(self, request: rec_pb2.UpsertUserRequest, context):
        user_id = request.userid

        calibration_size = request.calibration_size
        if calibration_size is not None and calibration_size < 0:
            log.warning(
                "calibration_size must be >= 0",
                extra={
                    "method": "ResetUser",
                    "user_id": user_id,
                    "calibration_size": calibration_size,
                    "status": "INVALID_ARGUMENT_ERROR",
                },
            )
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "calibration_size must be >= 0"
            )

        success = await self._rec_service.reset_user(
            user_id=user_id, calibration_size=calibration_size
        )

        log.info(
            "Reset user preference",
            extra={
                "method": "ResetUser",
                "user_id": user_id,
                "status": "OK",
            },
        )

        return rec_pb2.ResetUserResponse(success=success)


async def serve() -> None:
    host = os.getenv("REC_GRPC_HOST", "0.0.0.0")
    port = int(os.getenv("REC_GRPC_PORT", "50051"))

    init_langs(csv_path=os.getenv("PATH_TO_LANGS", "langs.csv"))
    setup_logging()

    db_config = DBConfig.from_env()
    engine = create_engine(db_config)
    uow_factory = make_uow_factory(create_sessionmaker(engine))

    rec_service_cfg = RecServiceConfig.from_env()
    rec_service = RecService(uow_factory=uow_factory, cfg=rec_service_cfg)

    pool_service = PoolService(uow_factory=uow_factory)

    server = grpc.aio.server(
        options=[
            ("grpc.max_send_message_length", 10 * 1024 * 1024),
            ("grpc.max_receive_message_length", 10 * 1024 * 1024),
        ]
    )
    rec_pb2_grpc.add_RecServiceServicer_to_server(
        RecGrpcServicer(rec_service=rec_service, pool_service=pool_service), server
    )

    server.add_insecure_port(f"{host}:{port}")
    log.info("Starting gRPC server...")
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
