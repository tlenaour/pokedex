import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fullstack_pokedex.api.middleware import (
    DEFAULT_CACHE_MAX_AGE,
    CacheControlMiddleware,
)
from fullstack_pokedex.api.routes import AppearanceIndexUnavailableError, router
from fullstack_pokedex.domain.errors import (
    InvalidReportError,
    InvalidSearchQueryError,
    NotFoundError,
)
from fullstack_pokedex.infrastructure.sqlite.feedback import init_feedback_db


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

    app = FastAPI(title="Pokédex API")
    app.state.db_path = db_path
    app.state.feedback_db_path = feedback_db_path
    app.include_router(router)
    app.add_middleware(CacheControlMiddleware, max_age=cache_max_age)

    @app.exception_handler(NotFoundError)
    def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(AppearanceIndexUnavailableError)
    def appearance_index_unavailable(
        _: Request, exc: AppearanceIndexUnavailableError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(InvalidSearchQueryError)
    @app.exception_handler(InvalidReportError)
    def invalid_input(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return app
