"""CacheControlMiddleware, tested on a minimal app: no database, no mock."""

import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient

from fullstack_pokedex.api.middleware import (
    DEFAULT_CACHE_MAX_AGE,
    CacheControlMiddleware,
)


def make_client(**middleware_options: int) -> TestClient:
    app = FastAPI()
    app.add_middleware(CacheControlMiddleware, **middleware_options)

    # FastAPI does not answer HEAD on @app.get routes (405): declare it.
    @app.api_route("/ok", methods=["GET", "HEAD"])
    def ok() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ok")
    def post() -> dict[str, str]:
        return {"status": "created"}

    @app.get("/missing")
    def missing() -> None:
        raise HTTPException(status_code=404)

    @app.get("/invalid")
    def invalid(n: int) -> int:
        return n

    @app.get("/crash")
    def crash() -> Response:
        return Response(status_code=500)

    @app.get("/custom")
    def custom(response: Response) -> dict[str, str]:
        response.headers["Cache-Control"] = "no-store"
        return {"status": "ok"}

    return TestClient(app)


@pytest.fixture
def client() -> TestClient:
    return make_client()


def test_successful_get_is_cacheable(client: TestClient) -> None:
    response = client.get("/ok")
    assert response.headers["cache-control"] == (
        f"public, max-age={DEFAULT_CACHE_MAX_AGE}"
    )


def test_head_is_cacheable_too(client: TestClient) -> None:
    assert "public" in client.head("/ok").headers["cache-control"]


def test_max_age_is_configurable() -> None:
    response = make_client(max_age=60).get("/ok")
    assert response.headers["cache-control"] == "public, max-age=60"


def test_negative_max_age_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_age"):
        make_client(max_age=-1).get("/ok")


@pytest.mark.parametrize(
    "path, status",
    [("/missing", 404), ("/invalid?n=abc", 422), ("/crash", 500)],
)
def test_errors_are_never_cached(client: TestClient, path: str, status: int) -> None:
    response = client.get(path)
    assert response.status_code == status
    assert "cache-control" not in response.headers


def test_writes_are_never_cached(client: TestClient) -> None:
    assert "cache-control" not in client.post("/ok").headers


def test_route_own_cache_control_is_kept(client: TestClient) -> None:
    assert client.get("/custom").headers["cache-control"] == "no-store"
