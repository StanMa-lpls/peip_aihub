"""
zh: 算法响应序列化模块，提供通用的 JSON 友好数据转换能力。
    算法 wrapper 可用该模块把 Pydantic 模型、带 to_dict() 的对象、映射、序列和值对象统一转换为
    peip_aihub 可编排、可返回的基础 Python 数据结构。
en: Algorithm response serialization module, providing shared JSON-friendly conversion.
    Algorithm wrappers use this module to convert Pydantic models, objects with to_dict(), mappings, sequences,
    and scalar values into plain Python data structures that peip_aihub can orchestrate and return.
version: 0.1.0
author: stan ma
date: 2026-07-01
mail: botao.ma@laplace-tech.com
"""

from __future__ import annotations

from typing import Any, Mapping


def to_jsonable(value: Any) -> Any:
    """
    zh: 将算法返回值转换为 JSON 友好的基础数据结构。
    en: Convert algorithm return values into JSON-friendly primitive structures.
    """
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_jsonable(value.to_dict())
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return to_jsonable(value.model_dump(mode="json"))
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return to_jsonable(vars(value))
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
