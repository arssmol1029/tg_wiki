import grpc
from wiki_service.service.http import HttpRequestError


def map_http_error(e: HttpRequestError) -> grpc.StatusCode:
    sc = e.status_code

    if sc == 429:
        return grpc.StatusCode.RESOURCE_EXHAUSTED

    if sc is None:
        return grpc.StatusCode.UNAVAILABLE

    if 500 <= sc <= 599:
        return grpc.StatusCode.UNAVAILABLE

    if sc == 404:
        return grpc.StatusCode.NOT_FOUND

    return grpc.StatusCode.INTERNAL
