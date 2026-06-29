"""Business service for configured algorithms."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.algorithms.exceptions import AlgorithmNotFoundError
from app.algorithms.io import describe_io_models
from app.algorithms.registry import AlgorithmRegistry
from app.core.settings import settings


@lru_cache(maxsize=1)
def get_algorithm_registry() -> AlgorithmRegistry:
    """Load the configured algorithm registry once per process.
    Use lru_cache to cache the result, so that the registry is not loaded every time.
    """

    return AlgorithmRegistry.from_file(settings.ALGORITHM_CONFIG_FILE)


def list_algorithms(registry: AlgorithmRegistry) -> list[dict]:
    """Return registered algorithm summaries."""

    items: list[dict] = []
    for algorithm_id in registry.algorithm_ids:
        spec = registry.get_spec(algorithm_id)
        if spec is None:
            continue
        items.append({
            "algorithm_id": spec.algorithm_id,
            "family": spec.family,
            "package": spec.package,
            "class_path": spec.class_path,
            "cached": spec.cache,
        })
    return items


def invoke_algorithm(registry: AlgorithmRegistry, algorithm_id: str, payload: dict) -> dict:
    """Invoke one configured algorithm and return a service result."""

    return {
        "algorithm_id": algorithm_id,
        "result": registry.invoke(algorithm_id, payload),
    }


def invoke_algorithm_capability(
    registry: AlgorithmRegistry,
    algorithm_id: str,
    capability: str,
    payload: Any,
) -> Any:
    """Invoke one declared algorithm capability through the registry."""

    return registry.invoke_capability(algorithm_id, capability, payload)


def call_algorithm_capability(
    algorithm_id: str,
    capability: str,
    payload: Any,
    *,
    registry: AlgorithmRegistry | None = None,
) -> Any:
    """Invoke one declared algorithm capability using the process registry."""

    active_registry = registry or get_algorithm_registry()
    return invoke_algorithm_capability(active_registry, algorithm_id, capability, payload)


def get_algorithm_metadata(registry: AlgorithmRegistry, algorithm_id: str) -> dict:
    """Return configured metadata for one algorithm."""

    spec = registry.get_spec(algorithm_id)
    if spec is None:
        raise AlgorithmNotFoundError(
            f"unknown algorithm_id={algorithm_id!r}; registered: {', '.join(registry.algorithm_ids)}"
        )
    return {
        "algorithm_id": spec.algorithm_id,
        "metadata": dict(spec.metadata),
    }


def get_algorithm_io(registry: AlgorithmRegistry, algorithm_id: str) -> dict:
    """Return configured input/output model information for one algorithm."""

    spec = registry.get_spec(algorithm_id)
    if spec is None:
        raise AlgorithmNotFoundError(
            f"unknown algorithm_id={algorithm_id!r}; registered: {', '.join(registry.algorithm_ids)}"
        )
    return describe_io_models(spec)
