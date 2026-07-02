"""Temperature algorithm metadata for OEE_Test."""

from __future__ import annotations

from oee_engine.common import BaseAlgorithmMetadata


class TemperatureAlgorithmMetadata(BaseAlgorithmMetadata):
    algorithm_id: str = "oee.temperature_detector"
    family: str = "oee"
    provider: str = "oee_engine"
    description: str = "OEE_Test 温度曲线伪异常检测器"
    when_to_use: str = "当报警上下文包含温区温度、设定值或温度时序曲线时，用于温度异常检测。"
    input_model: str = "oee_engine.temperature.TemperatureInput"
    output_model: str = "oee_engine.temperature.TemperatureEvent"
    tags: tuple[str, ...] = ("oee", "sensor_analysis", "temperature")
    class_path: str = "oee_engine.temperature.TemperatureController"
