"""Metadata-aware APC algorithm wrapper.

APCAlgorithm is the peip-facing capability object. It owns identity and request
boundaries while the wheel domain models remain the only APC input/output
models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from apc_engine.controller import APCEngineController
from apc_engine.domain import APCInput, APCResult


class SupportsAPCController(Protocol):
    @property
    def algorithm_id(self) -> str: ...

    def process_data(self, apc_input: APCInput | None = None) -> dict[str, Any]: ...

    def control(self, data: dict[str, Any] | None = None) -> APCResult: ...

    def adjust(self, apc_input: APCInput | None = None) -> APCResult: ...


@dataclass(frozen=True, slots=True)
class APCAlgorithmMetadata:
    """Stable identity and capability metadata for peip management."""

    algorithm_id: str
    family: str = "apc"
    version: str = "0.1.0"
    provider: str = "apc_engine"
    description: str = "用于集成测试的伪 Run-to-Run APC 控制器"
    when_to_use: str = "当需要根据机台、管号、目标工艺指标和工艺测量数据生成 APC 调整量时使用。"
    capabilities: tuple[str, ...] = ("adjust", "process_data", "control")
    input_model: str = "apc_engine.APCInput"
    output_model: str = "apc_engine.APCResult"
    tags: tuple[str, ...] = ("apc", "r2r")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None) -> "APCAlgorithmMetadata":
        payload = dict(payload or {})
        algorithm_id = str(payload.get("algorithm_id", "")).strip()
        if not algorithm_id:
            algorithm_id = "apc.test.r2r_controller"
        return cls(
            algorithm_id=algorithm_id,
            family=str(payload.get("family", "apc")),
            version=str(payload.get("version", "0.1.0")),
            provider=str(payload.get("provider", "apc_engine")),
            description=str(
                payload.get(
                    "description",
                    "用于集成测试的伪 Run-to-Run APC 控制器",
                )
            ),
            when_to_use=str(
                payload.get(
                    "when_to_use",
                    "当需要根据机台、管号、目标工艺指标和工艺测量数据生成 APC 调整量时使用。",
                )
            ),
            capabilities=tuple(str(item) for item in payload.get("capabilities", ("adjust", "process_data", "control"))),
            input_model=str(payload.get("input_model", "apc_engine.APCInput")),
            output_model=str(payload.get("output_model") or payload.get("result_model", "apc_engine.APCResult")),
            tags=tuple(str(item) for item in payload.get("tags", ("apc", "r2r"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm_id": self.algorithm_id,
            "family": self.family,
            "version": self.version,
            "provider": self.provider,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "capabilities": list(self.capabilities),
            "input_model": self.input_model,
            "output_model": self.output_model,
            "result_model": self.output_model,
            "tags": list(self.tags),
        }


class APCAlgorithm:
    """Single peip-facing APC capability wrapper."""

    def __init__(
        self,
        metadata: APCAlgorithmMetadata,
        *,
        controller: SupportsAPCController | None = None,
    ) -> None:
        self._metadata = metadata
        self._controller = controller or APCEngineController()

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
