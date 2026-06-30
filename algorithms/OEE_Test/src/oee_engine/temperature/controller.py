"""Pseudo temperature anomaly controller used by OEE_Test."""

from __future__ import annotations

from statistics import mean
from typing import Any, Mapping

from oee_engine.common import coerce_sensors, first_mean, first_timestamp, max_range, numeric_values
from oee_engine.temperature.domain import TemperatureEvent, TemperatureInput


class TemperatureController:
    """Independent temperature algorithm with process_data + detect capabilities."""

    DEFAULT_ALGORITHM_ID = "oee.temperature_detector"
    family = "oee"
    version = "0.1.0"
    provider = "oee_engine"
    sensor_type = "temperature"
    description = "OEE_Test 温度曲线伪异常检测器"
    when_to_use = "当报警上下文包含温区温度、设定值或温度时序曲线时，用于温度异常检测。"
    capabilities = ("process_data", "detect")
    tags = ("oee", "sensor_analysis", "temperature")
    input_model = "oee_engine.temperature.TemperatureInput"
    output_model = "oee_engine.temperature.TemperatureEvent"
    class_path = "oee_engine.temperature.TemperatureController"

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        self.params = dict(params or {})
        self.data_mat: dict[str, Any] | None = None

    @property
    def algorithm_id(self) -> str:
        return self.DEFAULT_ALGORITHM_ID

    @classmethod
    def metadata_defaults(cls) -> dict[str, Any]:
        return {
            "algorithm_id": cls.DEFAULT_ALGORITHM_ID,
            "family": cls.family,
            "version": cls.version,
            "provider": cls.provider,
            "description": cls.description,
            "when_to_use": cls.when_to_use,
            "capabilities": list(cls.capabilities),
            "tags": list(cls.tags),
            "input_model": cls.input_model,
            "output_model": cls.output_model,
            "class_path": cls.class_path,
        }

    def process_data(self, payload: Mapping[str, Any] | TemperatureInput | None = None) -> dict[str, Any]:
        temperature_input = TemperatureInput.from_payload(payload)
        sensors = coerce_sensors(temperature_input, default_name="temperature")
        processed = {
            "algorithm_id": self.algorithm_id,
            "sensor_type": self.sensor_type,
            "alarm_index": temperature_input.alarm_index,
            "alarm_reason": temperature_input.alarm_reason,
            "conventional_solution": temperature_input.conventional_solution,
            "sensors": sensors,
            "sensor_count": len(sensors),
            "params": {**temperature_input.params, **self.params},
            "pseudo_features": {
                "mean_temperature": first_mean(sensors),
                "max_temperature_range": max_range(sensors),
            },
        }
        self.data_mat = processed
        return processed

    def detect(self, data: dict[str, Any] | None = None) -> list[TemperatureEvent]:
        processed = data if isinstance(data, dict) else self.data_mat
        if not isinstance(processed, dict):
            return []

        params = dict(processed.get("params") or {})
        threshold = float(params.get("score_threshold", 0.3))
        max_events = int(params.get("max_events", 3))
        events: list[TemperatureEvent] = []
        for sensor in processed.get("sensors", []):
            values = numeric_values(sensor)
            if not values:
                continue
            baseline = mean(values)
            value = max(values, key=lambda item: abs(item - baseline))
            # Pseudo temperature logic: wider swings are treated as lower score
            # sensitivity than pressure, so the default threshold is higher.
            score = abs(value - baseline) / (abs(baseline) + 10.0)
            if score < threshold:
                continue
            events.append(
                TemperatureEvent(
                    name=str(sensor.get("name", "temperature")),
                    coordinate=str(sensor.get("coordinate", "")),
                    time=first_timestamp(sensor),
                    normal=round(float(baseline), 6),
                    value=round(float(value), 6),
                    score=round(float(score), 6),
                    algorithm_id=self.algorithm_id,
                    sensor_type=self.sensor_type,
                )
            )
            if len(events) >= max_events:
                break
        return events
