"""Public factory functions for peip-side discovery and loading."""

from __future__ import annotations

from typing import Any, Mapping

from apc_engine.algorithm import APCAlgorithm, APCAlgorithmMetadata


def create_algorithm(config: Mapping[str, Any] | None = None) -> APCAlgorithm:
    """Create one APCAlgorithm from peip-owned config."""
    config = dict(config or {})
    metadata = APCAlgorithmMetadata.from_dict(config.get("metadata") or config)
    return APCAlgorithm(metadata)


def get_algorithm_metadata(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return metadata without constructing or invoking the controller."""
    config = dict(config or {})
    return APCAlgorithmMetadata.from_dict(config.get("metadata") or config).to_dict()
