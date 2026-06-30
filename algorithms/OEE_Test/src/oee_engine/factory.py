"""Public factory functions for peip-side discovery and loading."""

from __future__ import annotations

from typing import Any, Mapping

from oee_engine.algorithm import (
    SensorAnalysisAlgorithm,
    SensorAnalysisAlgorithmMetadata,
)
from oee_engine.domain import get_supported_algorithms as _get_supported_algorithms


def create_algorithm(config: Mapping[str, Any] | None = None) -> SensorAnalysisAlgorithm:
    """Create one OEE_Test sensor-analysis algorithm from peip-owned config."""
    config = dict(config or {})
    metadata = SensorAnalysisAlgorithmMetadata.from_dict(config.get("metadata") or config)
    return SensorAnalysisAlgorithm(metadata, config=config)


def get_algorithm_metadata(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return metadata without constructing or invoking the controller."""
    config = dict(config or {})
    return SensorAnalysisAlgorithmMetadata.from_dict(config.get("metadata") or config).to_dict()


def get_supported_algorithms() -> list[str]:
    """Return the algorithm IDs provided by this aggregate package."""
    return _get_supported_algorithms()
