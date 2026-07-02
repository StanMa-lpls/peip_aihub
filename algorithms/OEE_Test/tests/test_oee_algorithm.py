from __future__ import annotations

from oee_engine import (
    PressureAlgorithmMetadata,
    PressureEvent,
    PressureInput,
    SensorAnalysisAlgorithm,
    SensorAnalysisAlgorithmMetadata,
    TemperatureAlgorithmMetadata,
    TemperatureEvent,
    TemperatureInput,
    create_algorithm,
    get_algorithm_metadata,
    get_supported_algorithms,
)
from oee_engine.common import BaseAlgorithmMetadata, BaseDetectAlgorithm, BaseOeeInput, BaseOeeOutput
from oee_engine.domain import ALGORITHM_CONTROLLERS
from oee_engine.pressure import PressureController
from oee_engine.temperature import TemperatureController


EXPECTED_ALGORITHM_IDS = {
    "oee.temperature_detector",
    "oee.pressure_detector",
}

EXPECTED_MODELS = {
    "oee.temperature_detector": (
        "oee_engine.temperature.TemperatureInput",
        "oee_engine.temperature.TemperatureEvent",
        "oee_engine.temperature.TemperatureController",
    ),
    "oee.pressure_detector": (
        "oee_engine.pressure.PressureInput",
        "oee_engine.pressure.PressureEvent",
        "oee_engine.pressure.PressureController",
    ),
}

REQUIRED_METADATA_KEYS = {
    "algorithm_id",
    "family",
    "version",
    "provider",
    "description",
    "when_to_use",
    "capabilities",
    "input_model",
    "output_model",
    "tags",
    "class_path",
}


def _payload(sensor_name: str = "demo_sensor") -> dict:
    return {
        "alarm_index": "demo_alarm",
        "alarm_reason": "demo sensor anomaly",
        "conventional_solution": "check sensor and actuator",
        "sensor_name": sensor_name,
        "coordinate": "demo-coordinate",
        "timestamps": ["2026-05-14 20:03:51", "2026-05-14 20:03:52"],
        "values": [1.0, 20.0],
    }


def test_supported_algorithm_ids_match_oee_sensor_analysis_registry() -> None:
    assert set(get_supported_algorithms()) == EXPECTED_ALGORITHM_IDS
    assert set(ALGORITHM_CONTROLLERS) == EXPECTED_ALGORITHM_IDS


def test_metadata_declares_internal_process_and_detect_capabilities() -> None:
    for algorithm_id in EXPECTED_ALGORITHM_IDS:
        metadata = get_algorithm_metadata({"algorithm_id": algorithm_id})
        input_model, output_model, class_path = EXPECTED_MODELS[algorithm_id]

        assert REQUIRED_METADATA_KEYS <= set(metadata)
        assert metadata["algorithm_id"] == algorithm_id
        assert metadata["family"] == "oee"
        assert metadata["version"] == "0.1.0"
        assert metadata["provider"] == "oee_engine"
        assert metadata["capabilities"] == ["process_data", "detect"]
        assert metadata["input_model"] == input_model
        assert metadata["output_model"] == output_model
        assert metadata["class_path"] == class_path
        assert "api_path" not in metadata
        assert "call" not in metadata


def test_child_controllers_expose_standard_metadata() -> None:
    controllers = {
        "oee.temperature_detector": (TemperatureController(), TemperatureAlgorithmMetadata),
        "oee.pressure_detector": (PressureController(), PressureAlgorithmMetadata),
    }

    for algorithm_id, (controller, metadata_cls) in controllers.items():
        metadata = controller.metadata
        metadata_dict = metadata.to_dict()

        assert isinstance(metadata, metadata_cls)
        assert REQUIRED_METADATA_KEYS <= set(metadata_dict)
        assert metadata_dict["algorithm_id"] == algorithm_id
        assert metadata_dict["family"] == "oee"
        assert metadata_dict["version"] == "0.1.0"
        assert metadata_dict["provider"] == "oee_engine"
        assert metadata_dict["capabilities"] == ["process_data", "detect"]


def test_oee_domain_models_use_common_oee_bases() -> None:
    assert issubclass(PressureInput, BaseOeeInput)
    assert issubclass(TemperatureInput, BaseOeeInput)
    assert issubclass(PressureEvent, BaseOeeOutput)
    assert issubclass(TemperatureEvent, BaseOeeOutput)


def test_sensor_analysis_algorithm_is_detect_algorithm() -> None:
    algorithm = create_algorithm({"metadata": {"algorithm_id": "oee.pressure_detector"}})

    assert isinstance(algorithm, SensorAnalysisAlgorithm)
    assert isinstance(algorithm, BaseDetectAlgorithm)


def test_detect_algorithm_validation_requires_detect_capability() -> None:
    class MissingDetectCapabilityAlgorithm(BaseDetectAlgorithm):
        def __init__(self) -> None:
            self._metadata = BaseAlgorithmMetadata(
                algorithm_id="oee.test.missing_detect_capability",
                capabilities=("process_data",),
            )

        @property
        def metadata(self) -> BaseAlgorithmMetadata:
            return self._metadata

        def process_data(self, payload=None) -> dict:
            return {}

        def detect(self, data=None) -> list:
            return []

    try:
        MissingDetectCapabilityAlgorithm().validate_capabilities()
    except ValueError as exc:
        assert "requires capability: detect" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_detect_algorithm_validation_requires_detect_method() -> None:
    class MissingDetectMethodAlgorithm(BaseDetectAlgorithm):
        def __init__(self) -> None:
            self._metadata = BaseAlgorithmMetadata(
                algorithm_id="oee.test.missing_detect_method",
                capabilities=("process_data", "detect"),
            )

        @property
        def metadata(self) -> BaseAlgorithmMetadata:
            return self._metadata

        def process_data(self, payload=None) -> dict:
            return {}

    try:
        MissingDetectMethodAlgorithm().validate_capabilities()
    except ValueError as exc:
        assert "missing capability methods" in str(exc)
        assert "detect" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_metadata_accepts_registry_style_config() -> None:
    metadata = get_algorithm_metadata(
        {
            "package": "oee-engine",
            "class_path": "oee_engine.create_algorithm",
            "metadata": {
                "algorithm_id": "oee.pressure_detector",
            },
        }
    )

    assert metadata["algorithm_id"] == "oee.pressure_detector"
    assert metadata["input_model"] == "oee_engine.pressure.PressureInput"
    assert metadata["output_model"] == "oee_engine.pressure.PressureEvent"


def test_factory_creates_each_detector_with_process_data_and_detect() -> None:
    for algorithm_id in EXPECTED_ALGORITHM_IDS:
        algorithm = create_algorithm(
            {
                "metadata": {
                    "algorithm_id": algorithm_id,
                },
                "use_external_backend": False,
            }
        )

        processed = algorithm.process_data(_payload(sensor_name=algorithm_id.rsplit(".", 1)[-1]))
        result = algorithm.detect(processed)

        assert algorithm.algorithm_id == algorithm_id
        assert processed["algorithm_id"] == algorithm_id
        assert processed["sensor_count"] == 1
        assert processed["params"]
        assert result
        assert result[0]["algorithm_id"] == algorithm_id


def test_input_models_provide_default_params_without_config() -> None:
    pressure = create_algorithm({"metadata": {"algorithm_id": "oee.pressure_detector"}})
    temperature = create_algorithm({"metadata": {"algorithm_id": "oee.temperature_detector"}})

    pressure_processed = pressure.process_data(_payload())
    temperature_processed = temperature.process_data(_payload())

    assert pressure_processed["params"] == {"score_threshold": 0.02, "max_events": 1}
    assert temperature_processed["params"] == {"score_threshold": 0.3, "max_events": 3}


def test_metadata_object_rejects_unknown_algorithm_id() -> None:
    try:
        SensorAnalysisAlgorithmMetadata.from_dict({"algorithm_id": "oee.test.missing"})
    except ValueError as exc:
        assert "unknown OEE_Test sensor analysis algorithm_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_factory_accepts_registry_style_params() -> None:
    algorithm = create_algorithm(
        {
            "metadata": {
                "algorithm_id": "oee.pressure_detector",
            },
            "params": {
                "score_threshold": 0.01,
                "max_events": 1,
            },
            "use_external_backend": False,
        }
    )
    processed = algorithm.process_data(_payload())

    assert processed["params"]["score_threshold"] == 0.01
    assert len(algorithm.detect(processed)) == 1


def test_factory_accepts_constructor_kwargs_params() -> None:
    algorithm = create_algorithm(
        {
            "metadata": {
                "algorithm_id": "oee.temperature_detector",
            },
            "constructor": {
                "kwargs": {
                    "params": {
                        "score_threshold": 0.01,
                        "max_events": 1,
                    },
                },
            },
        }
    )
    processed = algorithm.process_data(_payload())

    assert processed["params"]["score_threshold"] == 0.01
    assert processed["params"]["max_events"] == 1
