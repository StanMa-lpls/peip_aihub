"""Metadata-aware OEE_Test sensor-analysis algorithm wrapper."""

from __future__ import annotations

from typing import Any, Mapping

from algorithms.core import BaseAlgorithmMetadata, BaseDetectAlgorithm, to_jsonable
from oee_engine.controller import OEEEngineController, SupportsSensorAnalysisDetector
from oee_engine.domain import get_supported_algorithms
from oee_engine.pressure.metadata import PressureAlgorithmMetadata
from oee_engine.temperature.metadata import TemperatureAlgorithmMetadata


class SensorAnalysisAlgorithmMetadata(BaseAlgorithmMetadata):
    """Stable identity and capability metadata for peip management."""

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None) -> BaseAlgorithmMetadata:
        payload = dict(payload or {})
        algorithm_id = str(payload.get("algorithm_id") or TemperatureAlgorithmMetadata().algorithm_id).strip()
        return _metadata_class(algorithm_id).from_dict(payload)


class SensorAnalysisAlgorithm(BaseDetectAlgorithm):
    """Peip-facing wrapper for one OEE_Test sensor-analysis detector."""

    def __init__(
        self,
        metadata: BaseAlgorithmMetadata,
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
        self.validate_capabilities()

    @property
    def metadata(self) -> BaseAlgorithmMetadata:
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

_METADATA_CLASSES = {
    TemperatureAlgorithmMetadata().algorithm_id: TemperatureAlgorithmMetadata,
    PressureAlgorithmMetadata().algorithm_id: PressureAlgorithmMetadata,
}


def _metadata_class(algorithm_id: str) -> type[BaseAlgorithmMetadata]:
    metadata_cls = _METADATA_CLASSES.get(algorithm_id)
    if metadata_cls is None:
        raise ValueError(
            f"unknown OEE_Test sensor analysis algorithm_id: {algorithm_id!r}; "
            f"supported: {', '.join(get_supported_algorithms())}"
        )
    return metadata_cls
