"""Algorithm registry and dispatch facade."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from app.algorithms.handle import AlgorithmHandle
from app.algorithms.exceptions import AlgorithmLoadError, AlgorithmNotFoundError
from app.algorithms.importing import import_object
from app.algorithms.loader import AlgorithmLoader
from app.algorithms.specs import AlgorithmSpec, parse_algorithm_specs
from app.core.settings import load_config_file


class AlgorithmRegistry:
    """Lazy registry for configured wheel-backed algorithms."""

    def __init__(
        self,
        specs: Mapping[str, AlgorithmSpec],
        *,
        loader: AlgorithmLoader | None = None,
    ) -> None:
        if not specs:
            raise ValueError("AlgorithmRegistry requires at least one algorithm spec")
        self._specs = {key: _with_algorithm_metadata(spec) for key, spec in specs.items()}
        self._loader = loader or AlgorithmLoader()
        self._handles: dict[str, AlgorithmHandle] = {}

    @classmethod
    def from_mapping(
        cls,
        config: Mapping[str, Any],
        *,
        loader: AlgorithmLoader | None = None,
    ) -> "AlgorithmRegistry":
        return cls(parse_algorithm_specs(config), loader=loader)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        loader: AlgorithmLoader | None = None,
    ) -> "AlgorithmRegistry":
        return cls.from_mapping(load_config_file(path), loader=loader)

    @property
    def algorithm_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    def get_spec(self, algorithm_id: str) -> AlgorithmSpec | None:
        return self._specs.get(_normalize_algorithm_id(algorithm_id))

    def require(self, algorithm_id: str) -> AlgorithmHandle:
        key = _normalize_algorithm_id(algorithm_id)
        spec = self._specs.get(key)
        if spec is None:
            raise AlgorithmNotFoundError(
                f"unknown algorithm_id={algorithm_id!r}; registered: {', '.join(self.algorithm_ids)}"
            )
        if spec.cache and key in self._handles:
            return self._handles[key]
        handle = AlgorithmHandle(spec=spec, instance=self._loader.load(spec))
        if spec.cache:
            self._handles[key] = handle
        return handle

    def invoke(self, algorithm_id: str, payload: Any) -> Any:
        return self.require(algorithm_id).invoke(payload)


def _normalize_algorithm_id(value: str) -> str:
    return value.strip() if isinstance(value, str) else ""


def _with_algorithm_metadata(spec: AlgorithmSpec) -> AlgorithmSpec:
    explicit_metadata = dict(spec.metadata)
    base_metadata = {
        "algorithm_id": spec.algorithm_id,
        "family": spec.family,
        **explicit_metadata,
    }
    wheel_metadata = _load_wheel_metadata(spec, base_metadata)
    metadata = {
        **wheel_metadata,
        **explicit_metadata,
    }
    metadata.setdefault("algorithm_id", spec.algorithm_id)
    metadata.setdefault("family", spec.family)
    return replace(
        spec,
        family=str(metadata.get("family", spec.family)),
        metadata=metadata,
    )


def _load_wheel_metadata(spec: AlgorithmSpec, metadata: dict[str, Any]) -> dict[str, Any]:
    provider = _metadata_provider(spec.class_path)
    if provider is None:
        return {}
    try:
        result = provider(metadata)
    except Exception:
        return {}
    return dict(result) if isinstance(result, Mapping) else {}


def _metadata_provider(class_path: str):
    try:
        obj = import_object(class_path)
    except AlgorithmLoadError:
        obj = None
    provider = getattr(obj, "get_algorithm_metadata", None)
    if callable(provider):
        return provider

    for provider_path in _metadata_provider_paths(class_path):
        try:
            provider = import_object(provider_path)
        except AlgorithmLoadError:
            continue
        if callable(provider):
            return provider
    return None


def _metadata_provider_paths(class_path: str) -> tuple[str, ...]:
    module_path, _, name = class_path.rpartition(".")
    if not module_path:
        return ()
    paths = [f"{module_path}.get_algorithm_metadata"]
    if name.startswith("create_"):
        suffix = name.removeprefix("create_")
        paths.append(f"{module_path}.get_{suffix}_metadata")
    return tuple(dict.fromkeys(paths))
