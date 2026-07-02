"""Pressure algorithm metadata for OEE_Test."""

from __future__ import annotations

from oee_engine.common import BaseAlgorithmMetadata


class PressureAlgorithmMetadata(BaseAlgorithmMetadata):
    algorithm_id: str = "oee.pressure_detector"
    family: str = "oee"
    provider: str = "oee_engine"
    description: str = "OEE_Test 压力波形伪异常检测器"
    when_to_use: str = "当报警上下文包含炉管压力、压力实际值或压力时序波形时，用于压力异常检测。"
    input_model: str = "oee_engine.pressure.PressureInput"
    output_model: str = "oee_engine.pressure.PressureEvent"
    tags: tuple[str, ...] = ("oee", "sensor_analysis", "pressure")
    class_path: str = "oee_engine.pressure.PressureController"
