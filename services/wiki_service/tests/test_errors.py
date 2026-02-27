import grpc

from wiki_service.internal.errors import map_http_error, HttpRequestError


def test_map_429():
    e = HttpRequestError("rate limit", status_code=429, is_transient=True)
    assert map_http_error(e) == grpc.StatusCode.RESOURCE_EXHAUSTED


def test_map_transport():
    e = HttpRequestError("timeout", status_code=None, is_transient=True)
    assert map_http_error(e) == grpc.StatusCode.UNAVAILABLE


def test_map_5xx():
    e = HttpRequestError("bad gateway", status_code=502, is_transient=True)
    assert map_http_error(e) == grpc.StatusCode.UNAVAILABLE


def test_map_404():
    e = HttpRequestError("not found", status_code=404, is_transient=False)
    assert map_http_error(e) == grpc.StatusCode.NOT_FOUND
