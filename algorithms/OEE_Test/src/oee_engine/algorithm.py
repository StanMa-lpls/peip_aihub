"""Metadata-aware OEE_Test sensor-analysis algorithm wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from oee_engine.common import to_jsonable
from oee_engine.controller import OEEEngineController, SupportsSensorAnalysisDetector, load_controller_class


@dataclass(frozen=True, slots=True)
class SensorAnalysisAlgorithmMetadata:
    """Stable identity and capability metadata for peip management."""

    algorithm_id: str
    family: str = "oee"
    version: str = "0.1.0"
    provider: str = "oee_engine"
    description: str = "用于集成测试的 OEE 传感器伪异常检测器"
    when_to_use: str = "当需要根据报警上下文和传感器时序数据检测 OEE 传感器异常时使用。"
    capabilities: tuple[str, ...] = ("process_data", "detect")
    input_model: str = "dict"
    output_model: str = "list[dict]"
    tags: tuple[str, ...] = ("oee", "sensor_analysis")
    class_path: str = ""

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None) -> "SensorAnalysisAlgorithmMetadata":
        payload = dict(payload or {})
        algorithm_id = str(payload.get("algorithm_id") or "oee.temperature_detector").strip()
        defaults = _controller_metadata_defaults(load_controller_class(algorithm_id))
        return cls(
            algorithm_id=algorithm_id,
            family=str(payload.get("family", defaults["family"])),
            version=str(payload.get("version", defaults["version"])),
            provider=str(payload.get("provider", defaults["provider"])),
            description=str(payload.get("description", defaults["description"])),
            when_to_use=str(payload.get("when_to_use", defaults["when_to_use"])),
            capabilities=tuple(str(item) for item in payload.get("capabilities", defaults["capabilities"])),
            input_model=str(payload.get("input_model", defaults["input_model"])),
            output_model=str(payload.get("output_model", defaults["output_model"])),
            tags=tuple(str(item) for item in payload.get("tags", defaults["tags"])),
            class_path=str(payload.get("class_path", defaults["class_path"])),
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
            "tags": list(self.tags),
            "class_path": self.class_path,
        }


class SensorAnalysisAlgorithm:
    """Peip-facing wrapper for one OEE_Test sensor-analysis detector."""

    def __init__(
        self,
        metadata: SensorAnalysisAlgorithmMetadata,
        *,
        detector: SupportsSensorAnalysisDetector | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        self._metadata = metadata
        self._config = dict(config or {})
        self._controller = OEEEngineController(
            metadata.algorithm_id,
            config=self._config,
            detector=detector,
        )

    @property
    def metadata(self) -> SensorAnalysisAlgorithmMetadata:
        return self._metadata

    @property
    def algorithm_id(self) -> str:
        return self._metadata.algorithm_id

    def process_data(self, payload: Any = None) -> dict[str, Any]:
        processed = self._controller.process_data(payload)
        if not isinstance(processed, dict):
            raise TypeError(f"{self.algorithm_id}.process_data() must return dict")
        return to_jsonable(processed)

    def detect(self, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = self._controller.detect(data)
        jsonable = to_jsonable(result)
        if isinstance(jsonable, list):
            return jsonable
        if jsonable is None:
            return []
        return [jsonable]

    def to_response(self, result: Any) -> Any:
        return to_jsonable(result)


def _controller_metadata_defaults(controller_cls: type) -> dict[str, Any]:
    provider = getattr(controller_cls, "metadata_defaults", None)
    if callable(provider):
        return dict(provider())
    return {
        "algorithm_id": str(getattr(controller_cls, "DEFAULT_ALGORITHM_ID", "")),
        "family": str(getattr(controller_cls, "family", "oee")),
        "version": str(getattr(controller_cls, "version", "0.1.0")),
        "provider": str(getattr(controller_cls, "provider", "oee_engine")),
        "description": str(getattr(controller_cls, "description", "")),
        "when_to_use": str(getattr(controller_cls, "when_to_use", "")),
        "capabilities": list(getattr(controller_cls, "capabilities", ())),
        "tags": list(getattr(controller_cls, "tags", ())),
        "input_model": str(getattr(controller_cls, "input_model", "dict")),
        "output_model": str(getattr(controller_cls, "output_model", "list[dict]")),
        "class_path": str(getattr(controller_cls, "class_path", "")),
    }
