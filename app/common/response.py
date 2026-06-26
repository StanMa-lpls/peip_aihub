"""Common response helpers."""

from __future__ import annotations

from typing import Any

from app.api.models.algorithm_model import ResponseModel


async def success(data: Any = None, message: str = "success") -> ResponseModel:
    return ResponseModel(code=0, message=message, data=data)


async def fail(message: str, *, code: int = 1, data: Any = None) -> ResponseModel:
    return ResponseModel(code=code, message=message, data=data)
