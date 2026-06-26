"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.router import route
from app.core.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.PROJECT_VERSION,
    )
    app.include_router(route)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("app.application:app", host="0.0.0.0", port=8000)
