import asyncio

from wiki_service.grpc_server import serve


def run() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    run()
