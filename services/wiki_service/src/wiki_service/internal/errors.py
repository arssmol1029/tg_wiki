import grpc


class HttpClientError(RuntimeError):
    """Base error for HTTP client failures."""


class HttpNotStartedError(HttpClientError):
    """Raised when client session is not started."""


class HttpRequestError(HttpClientError):
    """HTTP request failed (transport or non-2xx response)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        is_transient: bool = False,
        retry_after_sec: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.is_transient = is_transient
        self.retry_after_sec = retry_after_sec


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
