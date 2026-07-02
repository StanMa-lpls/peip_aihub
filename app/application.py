"""FastAPI application factory."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import route
from app.core.settings import settings


def _sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return validation errors without echoing request input."""

    return [
        {
            "type": error.get("type"),
            "loc": list(error.get("loc", ())),
            "msg": error.get("msg", "Invalid input"),
        }
        for error in errors
    ]


def _validation_error_messages(errors: list[dict[str, Any]]) -> list[str]:
    messages: list[str] = []
    for error in errors:
        loc = list(error.get("loc", ()))
        field_parts = loc[1:] if loc and loc[0] == "body" else loc
        field_path = ".".join(str(part) for part in field_parts)
        if error.get("type") == "missing" and field_path:
            messages.append(f"Missing required field: {field_path}")
        elif field_path:
            messages.append(f"Field validation failed: {field_path}, {error.get('msg', 'Invalid input')}")
        else:
            messages.append(error.get("msg", "Request validation failed"))
    return messages


async def request_validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "Request validation failed",
            "data": {
                "errors": _sanitize_validation_errors(errors),
                "messages": _validation_error_messages(errors),
            },
        },
    )


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        message = str(detail.get("message") or detail.get("error") or "Request failed")
        data = detail.get("data")
        if data is None:
            data = {key: value for key, value in detail.items() if key not in {"code", "message"}}
            data = data or None
    else:
        message = str(detail or "Request failed")
        data = {"error": message}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": message,
            "data": data,
        },
        headers=exc.headers,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.PROJECT_VERSION,
    )
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.include_router(route)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("app.application:app", host="0.0.0.0", port=8000)
