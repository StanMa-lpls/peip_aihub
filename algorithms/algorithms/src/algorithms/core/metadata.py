"""
zh: 算法 metadata 基类模块，定义算法注册、发现、编排和管理所需的稳定元信息契约。
    该模型使用 Pydantic 统一字段类型转换、默认值、不可变约束和 JSON 输出行为。
en: Base algorithm metadata module, defining the stable metadata contract required for algorithm registration,
    discovery, orchestration, and management.
    This model uses Pydantic to unify field coercion, defaults, immutability, and JSON output behavior.
version: 0.1.0
author: stan ma
date: 2026-07-01
mail: botao.ma@laplace-tech.com
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseAlgorithmMetadata(BaseModel):
    """
    zh: 算法元数据基类。
        algorithm_id: 算法唯一标识。
        family: 算法族，例如 apc、oee。
        capabilities: workflow 可编排调用的方法名。
        input_model / output_model: 算法包公开的数据契约路径。
        class_path: algorithm_id 对应的实现类路径。
    en: Base algorithm metadata model.
        algorithm_id: Unique algorithm identifier.
        family: Algorithm family, such as apc or oee.
        capabilities: Method names callable by workflow orchestration.
        input_model / output_model: Public data contract paths exposed by the algorithm package.
        class_path: Implementation class path for the algorithm_id.
    """

    model_config = ConfigDict(frozen=True)

    algorithm_id: str = Field(default="")
    family: str = Field(default="")
    version: str = Field(default="0.1.0")
    provider: str = Field(default="")
    description: str = Field(default="")
    when_to_use: str = Field(default="")
    capabilities: tuple[str, ...] = Field(default=("process_data", "detect"))
    input_model: str = Field(default="dict")
    output_model: str = Field(default="list[dict]")
    tags: tuple[str, ...] = Field(default=("algorithm",))
    class_path: str = Field(default="")

    @field_validator("algorithm_id", mode="before")
    @classmethod
    def normalize_algorithm_id(cls, value: Any) -> str:
        """
        zh: 规范化算法 ID，避免配置中的空白字符进入注册契约。
        en: Normalize the algorithm ID so surrounding whitespace never enters the registration contract.
        """
        return str(value or "").strip()

    @field_validator(
        "family",
        "version",
        "provider",
        "description",
        "when_to_use",
        "input_model",
        "output_model",
        "class_path",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        """
        zh: 将文本字段统一转换为字符串。
        en: Coerce text fields into strings consistently.
        """
        return str(value or "")

    @field_validator("capabilities", "tags", mode="before")
    @classmethod
    def normalize_tuple(cls, value: Any) -> tuple[str, ...]:
        """
        zh: 将 capabilities 与 tags 规范化为字符串元组。
        en: Normalize capabilities and tags into string tuples.
        """
        if value is None:
            return ()
        if isinstance(value, str):
            return (value,)
        if isinstance(value, list | tuple | set):
            return tuple(str(item) for item in value)
        return (str(value),)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None):
        """
        zh: 从配置字典创建 metadata 对象。
        en: Create a metadata object from a configuration mapping.
        """
        return cls(**dict(payload or {}))

    def to_dict(self) -> dict[str, Any]:
        """
        zh: 输出供 peip_aihub 注册、展示和编排使用的 metadata 字典。
        en: Return a metadata dictionary for peip_aihub registration, presentation, and orchestration.
        """
        return self.model_dump(mode="json")
