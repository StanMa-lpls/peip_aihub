"""OEE_Test sensor-analysis controller."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Mapping, Protocol

from oee_engine.domain import get_class_path


class SupportsSensorAnalysisDetector(Protocol):
    def process_data(self, payload: Any = None) -> dict[str, Any]: ...

    def detect(self, data: dict[str, Any] | None = None, **kwargs: Any) -> Any: ...


class OEEEngineController:
    """Metadata-compatible aggregate controller for one packaged algorithm."""

    def __init__(
        self,
        algorithm_id: str,
        *,
        config: Mapping[str, Any] | None = None,
        detector: SupportsSensorAnalysisDetector | None = None,
    ) -> None:
        self._algorithm_id = algorithm_id
        self._config = dict(config or {})
        self._controller_cls = load_controller_class(algorithm_id)
        self._detector = detector or self._build_detector()

    @property
    def algorithm_id(self) -> str:
        return self._algorithm_id

    def process_data(self, payload: Any = None) -> dict[str, Any]:
        return self._detector.process_data(payload)

    def detect(self, data: dict[str, Any] | None = None) -> Any:
        return self._detector.detect(data)

    def _build_detector(self) -> SupportsSensorAnalysisDetector:
        return self._controller_cls(_merged_params(self._controller_cls, self._config))


def load_controller_class(algorithm_id: str):
    class_path = get_class_path(algorithm_id)
    module_path, _, class_name = class_path.rpartition(".")
    module = import_module(module_path)
    return getattr(module, class_name)


def _merged_params(controller_cls: type, config: Mapping[str, Any]) -> dict[str, Any]:
    cfg = dict(config.get("cfg") or {})
    constructor = dict(config.get("constructor") or {})
    constructor_kwargs = dict(constructor.get("kwargs") or {})
    params: dict[str, Any] = {}
    params.update(dict(cfg.get("params") or {}))
    params.update(dict(constructor_kwargs.get("params") or {}))
    params.update(dict(config.get("params") or {}))
    return params
