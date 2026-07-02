"""OEE_Test aggregate sensor-analysis wheel public API."""

from oee_engine.algorithm import (
    SensorAnalysisAlgorithm,
    SensorAnalysisAlgorithmMetadata,
)
from oee_engine.controller import OEEEngineController
from oee_engine.domain import ALGORITHM_CONTROLLERS
from oee_engine.factory import create_algorithm, get_algorithm_metadata, get_supported_algorithms
from oee_engine.pressure import PressureAlgorithmMetadata, PressureEvent, PressureInput
from oee_engine.temperature import TemperatureAlgorithmMetadata, TemperatureEvent, TemperatureInput

__all__ = [
    "ALGORITHM_CONTROLLERS",
    "OEEEngineController",
    "PressureAlgorithmMetadata",
    "PressureEvent",
    "PressureInput",
    "SensorAnalysisAlgorithm",
    "SensorAnalysisAlgorithmMetadata",
    "TemperatureAlgorithmMetadata",
    "TemperatureEvent",
    "TemperatureInput",
    "create_algorithm",
    "get_algorithm_metadata",
    "get_supported_algorithms",
]
