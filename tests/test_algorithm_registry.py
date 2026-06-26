from __future__ import annotations

from app import AlgorithmRegistry


def test_pipeline_algorithm_invocation() -> None:
    registry = AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "anomaly.fake.oee": {
                    "family": "anomaly",
                    "class_path": "tests.fakes.FakeOEEAnalyzer",
                    "constructor": {
                        "mode": "positional",
                        "args": [
                            {
                                "factory": "tests.fakes.FakeCfg",
                                "value": {"params": {"threshold": 0.8}},
                            }
                        ],
                    },
                    "call": {
                        "mode": "pipeline",
                        "steps": ["process_data", "detect"],
                    },
                }
            }
        }
    )

    result = registry.invoke("anomaly.fake.oee", {"sensor": "temperature"})

    assert result == [{"name": "temperature", "score": 0.8}]


def test_method_algorithm_invocation_with_input_factory() -> None:
    registry = AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.fake": {
                    "family": "apc",
                    "class_path": "tests.fakes.FakeAPCController",
                    "call": {
                        "mode": "method",
                        "method": "adjust",
                        "input_factory": "tests.fakes.FakeAPCInput.from_dict",
                    },
                }
            }
        }
    )

    result = registry.invoke("apc.fake", {"machine_id": "M1"})

    assert result == {"adjustments": {"rb": [1.0, 0.0]}}


def test_registry_caches_loaded_handles() -> None:
    registry = AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.fake": {
                    "family": "apc",
                    "class_path": "tests.fakes.FakeAPCController",
                    "call": {
                        "mode": "method",
                        "method": "adjust",
                        "input_factory": "tests.fakes.FakeAPCInput.from_dict",
                    },
                }
            }
        }
    )

    assert registry.require("apc.fake") is registry.require("apc.fake")


def test_config_constructor_injects_spec_metadata() -> None:
    registry = AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.factory": {
                    "family": "apc",
                    "class_path": "tests.fakes.create_fake_algorithm",
                    "metadata": {
                        "algorithm_id": "apc.factory",
                        "version": "test",
                    },
                    "constructor": {
                        "mode": "config",
                        "kwargs": {"strict_process": True},
                    },
                    "call": {
                        "mode": "method",
                        "method": "invoke",
                    },
                }
            }
        }
    )

    result = registry.invoke("apc.factory", {"machine_id": "M1"})

    assert result == {
        "algorithm_id": "apc.factory",
        "family": "apc",
        "strict_process": True,
        "payload": {"machine_id": "M1"},
    }


def test_factory_algorithm_uses_default_config_constructor_and_auto_call() -> None:
    registry = AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.auto": {
                    "family": "apc",
                    "class_path": "tests.fakes.create_fake_adjust_algorithm",
                    "metadata": {
                        "algorithm_id": "apc.auto",
                    },
                }
            }
        }
    )

    result = registry.invoke("apc.auto", {"value": 2})

    assert result == {
        "adjustments": {"rb": [2.0]},
        "algorithm_id": "apc.auto",
    }


def test_metadata_models_parse_input_and_normalize_output() -> None:
    registry = AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.typed": {
                    "family": "apc",
                    "class_path": "tests.fakes.FakeTypedAPCController",
                    "metadata": {
                        "input_model": "tests.fakes.FakeAPCInput",
                        "output_model": "tests.fakes.FakeAPCResult",
                    },
                    "call": {
                        "mode": "method",
                        "method": "adjust",
                    },
                }
            }
        }
    )

    result = registry.invoke("apc.typed", {"machine_id": "M1"})

    assert result == {"adjustments": {"m1": [3.0]}}
