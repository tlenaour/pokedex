"""HTTP middlewares."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

DEFAULT_CACHE_MAX_AGE = 3600
"""Seconds. The data only changes when `pokedex-import` is run again, so a
client may reuse a response for an hour; after a re-import, it can see the
previous data until then."""

_CACHEABLE_METHODS = {"GET", "HEAD"}


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Let browsers and proxies reuse successful read responses.

    The API is read-only and its data is static: the same request always gets
    the same response (e.g. autocompletion re-typing the same letters).
    Errors (4xx/5xx) are never cached, so a transient error does not stick,
    and a route that sets its own Cache-Control keeps it.
    """

    def __init__(self, app: ASGIApp, max_age: int = DEFAULT_CACHE_MAX_AGE) -> None:
        super().__init__(app)
        if max_age < 0:
            raise ValueError(f"max_age must be >= 0, got {max_age}")
        self.header = f"public, max-age={max_age}"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if (
            request.method in _CACHEABLE_METHODS
            and 200 <= response.status_code < 300
            and "cache-control" not in response.headers
        ):
            response.headers["Cache-Control"] = self.header
        return response
