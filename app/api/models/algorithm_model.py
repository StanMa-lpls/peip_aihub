"""Pydantic models for algorithm APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    """Common API response envelope."""

    code: int = Field(default=200, description="HTTP-style status code")
    message: str = Field(default="success", description="Response message")
    data: Any = Field(default=None, description="Response data")
