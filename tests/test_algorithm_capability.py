from __future__ import annotations

import pytest

from app import AlgorithmRegistry
from app.algorithms.exceptions import AlgorithmInvocationError, AlgorithmNotFoundError
from app.algorithms.service import call_algorithm_capability, invoke_algorithm_capability


def _fake_registry() -> AlgorithmRegistry:
    return AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.fake": {
                    "family": "apc",
                    "class_path": "tests.fakes.FakeAPCController",
                }
            }
        }
    )


def test_handle_invoke_capability_invokes_declared_method() -> None:
    registry = _fake_registry()
    handle = registry.require("apc.fake")

    result = handle.invoke_capability("adjust", {"machine_id": "M1", "process": "LP"})

    assert result == {"adjustments": {"lp": [1.0, 0.0]}}


def test_registry_invoke_capability_invokes_declared_method() -> None:
    registry = _fake_registry()

    result = registry.invoke_capability(
        "apc.fake",
        "adjust",
        {"machine_id": "M1", "process": "LP"},
    )

    assert result == {"adjustments": {"lp": [1.0, 0.0]}}


def test_invoke_algorithm_capability_supports_pipeline_style_capabilities() -> None:
    registry = _fake_registry()
    payload = {"machine_id": "M1", "process": "RB"}

    features = invoke_algorithm_capability(registry, "apc.fake", "process_data", payload)
    result = invoke_algorithm_capability(registry, "apc.fake", "control", features)

    assert features == {"machine_id": "M1", "process": "RB"}
    assert result == {"adjustments": {"rb": [2.0, 0.0]}}


def test_call_algorithm_capability_uses_injected_registry() -> None:
    registry = _fake_registry()

    result = call_algorithm_capability(
        "apc.fake",
        "adjust",
        {"machine_id": "M1", "process": "RB"},
        registry=registry,
    )

    assert result == {"adjustments": {"rb": [1.0, 0.0]}}


def test_invoke_capability_rejects_unknown_capability() -> None:
    registry = _fake_registry()

    with pytest.raises(AlgorithmInvocationError, match="does not support capability 'detect'"):
        registry.invoke_capability("apc.fake", "detect", {"machine_id": "M1"})


def test_invoke_capability_rejects_unknown_algorithm() -> None:
    registry = _fake_registry()

    with pytest.raises(AlgorithmNotFoundError):
        registry.invoke_capability("apc.missing", "adjust", {"machine_id": "M1"})
