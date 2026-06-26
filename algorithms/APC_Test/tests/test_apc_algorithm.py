from __future__ import annotations

from apc_engine import (
    APCAlgorithmMetadata,
    APCInput,
    create_algorithm,
    get_algorithm_metadata,
)
from apc_engine.algorithm import APCAlgorithm


def _payload(process: str = "RB") -> dict:
    return {
        "algorithm_id": "apc.test.r2r_controller",
        "machine_id": "M01",
        "tube_id": "T01",
        "target_p": 100.0,
        "p_data": {"p1_mean": [96.0, 97.0, 98.0]},
        "adj_data": {},
        "adjust_max_limit": 2,
        "process": process,
    }


def test_algorithm_adjust_uses_metadata_identity() -> None:
    metadata = APCAlgorithmMetadata(
        algorithm_id="apc.test.r2r_controller",
        tags=("test",),
    )
    algorithm = APCAlgorithm(metadata)

    result = algorithm.adjust(_payload())
    response = algorithm.to_response(result)

    assert response["algorithm_id"] == "apc.test.r2r_controller"
    assert response["adjustments"]["temperature"]
    assert response["blocked_by_actuator"] == {}
    assert algorithm.metadata.to_dict()["input_model"] == "apc_engine.APCInput"


def test_algorithm_accepts_apc_input_without_dict_roundtrip() -> None:
    algorithm = APCAlgorithm(
        APCAlgorithmMetadata(
            algorithm_id="apc.test.r2r_controller",
        )
    )
    apc_input = APCInput.from_dict(_payload())

    result = algorithm.adjust(apc_input)

    assert result.algorithm_id == "apc.test.r2r_controller"


def test_algorithm_uses_input_process_for_each_request() -> None:
    algorithm = APCAlgorithm(
        APCAlgorithmMetadata(
            algorithm_id="apc.test.r2r_controller",
        )
    )
    payload = _payload("LP")
    payload["algorithm_id"] = "apc.test.r2r_controller"

    result = algorithm.adjust(payload)

    assert result.algorithm_id == "apc.test.r2r_controller"
    assert result.adjustments["temperature"]
    assert result.adjustments["flow"]


def test_public_factory_surface_for_peip() -> None:
    algorithm = create_algorithm(
        {
            "metadata": {
                "algorithm_id": "apc.test.r2r_controller",
                "version": "0.1.0",
            }
        }
    )
    metadata = get_algorithm_metadata(
        {
            "algorithm_id": "apc.test.r2r_controller",
        }
    )

    assert algorithm.algorithm_id == "apc.test.r2r_controller"
    assert metadata["input_model"] == "apc_engine.APCInput"
