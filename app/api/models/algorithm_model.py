"""Pydantic models for algorithm APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    """Common API response envelope."""

    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="success", description="响应消息")
    data: Any = Field(default=None, description="响应数据")
