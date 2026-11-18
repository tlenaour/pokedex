import argparse
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from fullstack_pokedex.api.middleware import (
    DEFAULT_CACHE_MAX_AGE,
    CacheControlMiddleware,
)
from fullstack_pokedex.api.routes import AppearanceIndexUnavailableError, router
from fullstack_pokedex.domain.errors import DomainError, NotFoundError
from fullstack_pokedex.infrastructure.sqlite.feedback import init_feedback_db

API_TITLE = "Pokédex API"

# HTTP status of a business error. Any other DomainError is a rule the request
# broke: 422. Kept here so that the domain stays free of HTTP.
_DOMAIN_ERROR_STATUS: dict[type[DomainError], int] = {NotFoundError: 404}

# The API's contract, versioned with the frontend that is built against it.
# Relative to the repository root (see `repository_root`).
OPENAPI_FILE = Path("frontend/openapi.json")


def create_app(
    db_path: Path | None = None,
    cache_max_age: int = DEFAULT_CACHE_MAX_AGE,
    feedback_db_path: Path | None = None,
) -> FastAPI:
    db_path = db_path or Path(os.environ.get("POKEDEX_DB", "pokedex.db"))
    if not db_path.is_file():
        raise RuntimeError(
            f"Database {db_path} not found: run `uv run pokedex-import` first."
        )

    # User feedback lives in its own database, next to pokedex.db by default:
    # `pokedex-import` rebuilds pokedex.db and must never erase it.
    feedback_db_path = feedback_db_path or Path(
        os.environ.get("POKEDEX_FEEDBACK_DB", db_path.with_name("feedback.db"))
    )
    init_feedback_db(feedback_db_path)

    app = FastAPI(title=API_TITLE)
    app.state.db_path = db_path
    app.state.feedback_db_path = feedback_db_path
    app.include_router(router)
    app.add_middleware(CacheControlMiddleware, max_age=cache_max_age)

    # One handler for every business error: a new DomainError can never
    # escape as a 500.
    @app.exception_handler(DomainError)
    def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status = next(
            (
                code
                for cls, code in _DOMAIN_ERROR_STATUS.items()
                if isinstance(exc, cls)
            ),
            422,
        )
        if status == 422:
            # Same shape as FastAPI's own validation errors, which is what the
            # OpenAPI (and the frontend's generated types) declare for a 422.
            detail: Any = [{"loc": [], "msg": str(exc), "type": "value_error"}]
        else:
            detail = str(exc)
        return JSONResponse(status_code=status, content={"detail": detail})

    @app.exception_handler(AppearanceIndexUnavailableError)
    def appearance_index_unavailable(
        _: Request, exc: AppearanceIndexUnavailableError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    return app


API_PREFIX = "/api"


def create_server(static_dir: Path | None = None) -> FastAPI:
    """What runs in production: the API under /api, and the built frontend.

    The frontend calls `/api/...` on its own origin. The prefix is carried
    here, by the backend, so the path is the same in development, in tests and
    in production: no proxy has to rewrite it. The API itself (`create_app`)
    keeps its routes at the root and is simply mounted under the prefix; its
    docs are at /api/docs.

    The frontend build (`pnpm build`) is served at `/` when `POKEDEX_STATIC_DIR`
    points to it: one process, one Docker image. Without it (development), only
    the API is served and Vite serves the frontend.
    """
    server = FastAPI(title="Pokédex", docs_url=None, redoc_url=None, openapi_url=None)
    server.mount(API_PREFIX, create_app())

    if static_dir is None and "POKEDEX_STATIC_DIR" in os.environ:
        static_dir = Path(os.environ["POKEDEX_STATIC_DIR"])
    if static_dir is not None:
        if not static_dir.is_dir():
            raise RuntimeError(
                f"Frontend build {static_dir} not found: run `pnpm build` first."
            )
        # Last: a mount at "/" catches everything the API did not.
        # `html=True` serves index.html at "/"; the app routes with the URL
        # hash, so no other path has to fall back to it.
        server.mount("/", StaticFiles(directory=static_dir, html=True))
    return server


def openapi_schema() -> dict[str, Any]:
    """The API's OpenAPI schema, built without a database or a server.

    Same title and routes as `create_app` (a test checks it): the frontend's
    TypeScript types are generated from it.
    """
    app = FastAPI(title=API_TITLE)
    app.include_router(router)
    return app.openapi()


def repository_root(start: Path) -> Path:
    """The repository containing `start`: the closest folder, from `start`
    upwards, that holds both `pyproject.toml` and `frontend/`.

    So `uv run pokedex-openapi` writes the same file from anywhere in the
    repository (the root, `frontend/`, `src/`…), not relative to the current
    folder. Not from the installed package's location: once installed in a
    venv, it is not inside the repository.
    """
    for folder in [start, *start.parents]:
        if (folder / "pyproject.toml").is_file() and (folder / "frontend").is_dir():
            return folder
    raise SystemExit(
        f"{start} is not inside the Pokédex repository: run this command from "
        "the repository, or give the file with --out."
    )


def export_openapi() -> None:
    """`uv run pokedex-openapi`: write the API's contract for the frontend.

    The file is versioned: a test fails as soon as it no longer matches the
    code, and the frontend's types are generated from it (`pnpm gen:api`).
    """
    parser = argparse.ArgumentParser(description=export_openapi.__doc__)
    parser.add_argument(
        "--out", type=Path, help="default: frontend/openapi.json of this repository"
    )
    out = parser.parse_args().out or repository_root(Path.cwd()) / OPENAPI_FILE
    text = json.dumps(openapi_schema(), indent=2, ensure_ascii=False)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {out}. Now run `cd frontend && pnpm gen:api`.")
