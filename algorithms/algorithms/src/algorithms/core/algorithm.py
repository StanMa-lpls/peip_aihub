"""
zh: 算法包装器基类模块，定义算法元数据访问、数据处理、响应序列化、检测/控制能力入口及能力完整性校验。
    若算法需要同时实现 detect 与 control，可继承 BaseAlgorithm 并同时实现 detect()、control()，
    同时在 metadata.capabilities 中声明 "detect" 和 "control"。
    若算法需要实现自定义 capability，可继承 BaseAlgorithm 或具体分类基类，并在 metadata.capabilities
    中声明自定义方法名；validate_capabilities() 会校验这些方法是否真实存在且不是基类占位实现。
en: Base wrapper module for algorithms, defining metadata access, data processing, response serialization,
    detect/control capability entry points, and capability integrity validation.
    If an algorithm needs both detect and control, inherit from BaseAlgorithm and implement both detect() and
    control(), then declare "detect" and "control" in metadata.capabilities.
    If an algorithm needs custom capabilities, inherit from BaseAlgorithm or a concrete category base class,
    then declare the custom method names in metadata.capabilities; validate_capabilities() checks that those
    methods exist and are not base-class stubs.
version: 0.1.0
author: stan ma
date: 2026-07-01
mail: botao.ma@laplace-tech.com
"""

from __future__ import annotations

from typing import Any, ClassVar

from algorithms.core.metadata import BaseAlgorithmMetadata
from algorithms.core.serialization import to_jsonable


class BaseAlgorithm:
    """
    zh: 算法包装器基类。
        required_capability: 算法需要的能力，可选值为 "detect"、"control" 或 None。
        metadata: 算法元数据，包括算法 ID、版本、能力、输入输出模型和实现路径等。
        algorithm_id: 算法唯一标识。
        process_data: 算法数据预处理入口。
        to_response: 将算法结果转换为响应格式。
        validate_capabilities: 验证算法声明的能力是否真实可调用。
    en: Base wrapper for algorithms.
        required_capability: The required capability, such as "detect", "control", or None.
        metadata: Algorithm metadata, including ID, version, capabilities, input/output models, and class path.
        algorithm_id: The unique algorithm identifier.
        process_data: Algorithm data preprocessing entry point.
        to_response: Convert algorithm results into response format.
        validate_capabilities: Validate that declared capabilities are actually callable.
    """

    required_capability: ClassVar[str | None] = None

    @property
    def metadata(self) -> BaseAlgorithmMetadata:
        """
        zh: 获取算法 metadata。
        en: Get algorithm metadata.
        """
        raise NotImplementedError

    @property
    def algorithm_id(self) -> str:
        """
        zh: 获取算法 ID。
        en: Get the algorithm ID.
        """
        return self.metadata.algorithm_id

    def process_data(self, payload: Any = None) -> dict[str, Any]:
        """
        zh: 处理输入数据并生成算法中间态。
        en: Process input data and produce algorithm intermediate state.
        """
        raise NotImplementedError

    def to_response(self, result: Any) -> Any:
        """
        zh: 将算法结果转换为 JSON 友好的响应格式。
        en: Convert algorithm results into a JSON-friendly response format.
        """
        return to_jsonable(result)

    def validate_capabilities(self) -> None:
        """
        zh:
            验证算法能力，如果 required_capability 不在 metadata.capabilities 中，或 metadata.capabilities
            声明的方法不存在 / 仍是基类占位实现，则抛出 ValueError。
        en:
            Validate algorithm capabilities. Raise ValueError when required_capability is absent from
            metadata.capabilities, or when a declared capability is missing / still a base-class stub.
        """
        capabilities = tuple(self.metadata.capabilities)
        if self.required_capability and self.required_capability not in capabilities:
            raise ValueError(
                f"{type(self).__name__} requires capability: {self.required_capability}"
            )

        missing = [
            capability
            for capability in capabilities
            if not _has_concrete_capability(self, capability)
        ]
        if missing:
            raise ValueError(f"missing capability methods: {missing}")


class BaseDetectAlgorithm(BaseAlgorithm):
    """
    zh: 检测类算法基类。
    en: Base wrapper for algorithms whose primary action is detect.
    """

    required_capability: ClassVar[str | None] = "detect"

    def detect(self, data: dict[str, Any] | None = None) -> Any:
        """
        zh: 检测类算法实现入口。
        en: Detect algorithm implementation entry point.
        """
        raise NotImplementedError


class BaseControlAlgorithm(BaseAlgorithm):
    """
    zh: 控制类算法基类。
    en: Base wrapper for algorithms whose primary action is control.
    """

    required_capability: ClassVar[str | None] = "control"

    def control(self, data: dict[str, Any] | None = None) -> Any:
        """
        zh: 控制类算法实现入口。
        en: Control algorithm implementation entry point.
        """
        raise NotImplementedError


_CAPABILITY_STUBS = {
    "process_data": BaseAlgorithm.process_data,
    "detect": BaseDetectAlgorithm.detect,
    "control": BaseControlAlgorithm.control,
}


def _has_concrete_capability(algorithm: BaseAlgorithm, capability: str) -> bool:
    """
    zh:
        判断算法是否真实实现了指定能力。
        如果方法只是继承自基类中的占位实现，则不认为是有效能力。
    en:
        Check whether the algorithm has a concrete implementation for the given capability.
        A method inherited from a base-class stub is not treated as a valid capability.
    """
    method = getattr(algorithm, capability, None)
    if not callable(method):
        return False

    class_method = getattr(type(algorithm), capability, None)
    return class_method is not _CAPABILITY_STUBS.get(capability)
