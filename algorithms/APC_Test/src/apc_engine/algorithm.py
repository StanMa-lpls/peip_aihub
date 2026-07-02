"""Metadata-aware APC algorithm wrapper.

APCAlgorithm is the peip-facing capability object. It owns identity and request
boundaries while the wheel domain models remain the only APC input/output
models.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from algorithms.core import BaseAlgorithmMetadata, BaseControlAlgorithm
from apc_engine.controller import APCEngineController
from apc_engine.domain import APCInput, APCResult


class SupportsAPCController(Protocol):
    @property
    def algorithm_id(self) -> str: ...

    def process_data(self, apc_input: APCInput | None = None) -> dict[str, Any]: ...

    def control(self, data: dict[str, Any] | None = None) -> APCResult: ...

    def adjust(self, apc_input: APCInput | None = None) -> APCResult: ...


class APCAlgorithmMetadata(BaseAlgorithmMetadata):
    """Stable identity and capability metadata for peip management."""

    algorithm_id: str = "apc.test.r2r_controller"
    family: str = "apc"
    version: str = "0.1.0"
    provider: str = "apc_engine"
    description: str = "用于集成测试的伪 Run-to-Run APC 控制器"
    when_to_use: str = "当需要根据机台、管号、目标工艺指标和工艺测量数据生成 APC 调整量时使用。"
    capabilities: tuple[str, ...] = ("adjust", "process_data", "control")
    input_model: str = "apc_engine.APCInput"
    output_model: str = "apc_engine.APCResult"
    tags: tuple[str, ...] = ("apc", "r2r")
    class_path: str = "apc_engine.APCEngineController"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None) -> "APCAlgorithmMetadata":
        payload = dict(payload or {})
        algorithm_id = str(payload.get("algorithm_id", "")).strip()
        if not algorithm_id:
            payload["algorithm_id"] = cls().algorithm_id
        return cls(**payload)


class APCAlgorithm(BaseControlAlgorithm):
    """Single peip-facing APC capability wrapper."""

    def __init__(
        self,
        metadata: APCAlgorithmMetadata,
        *,
        controller: SupportsAPCController | None = None,
    ) -> None:
        self._metadata = metadata
        self._controller = controller or APCEngineController()
        self.validate_capabilities()

    @property
    def metadata(self) -> APCAlgorithmMetadata:
        return self._metadata

    @property
    def algorithm_id(self) -> str:
        return self._metadata.algorithm_id

    def process_data(self, payload: Mapping[str, Any] | APCInput | None = None) -> dict[str, Any]:
        apc_input = APCInput.from_payload(payload)
        return self._controller.process_data(apc_input)

    def control(self, data: dict[str, Any] | None = None) -> APCResult:
        result = self._controller.control(data)
        result.algorithm_id = self.algorithm_id
        return result

    def adjust(self, payload: Mapping[str, Any] | APCInput | None = None) -> APCResult:
        apc_input = APCInput.from_payload(payload)
        result = self._controller.adjust(apc_input)
        result.algorithm_id = self.algorithm_id
        return result


    def to_response(self, result: APCResult) -> dict[str, Any]:
        result.algorithm_id = self.algorithm_id
        return result.to_dict()
