"""Pseudo pressure anomaly controller used by OEE_Test."""

from __future__ import annotations

from statistics import mean
from typing import Any, Mapping

from oee_engine.common import coerce_sensors, first_mean, first_timestamp, max_delta, numeric_values
from oee_engine.pressure.domain import PressureEvent, PressureInput
from oee_engine.pressure.metadata import PressureAlgorithmMetadata


class PressureController:
    """Independent pressure algorithm with process_data + detect capabilities."""

    sensor_type = "pressure"

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        self._metadata = PressureAlgorithmMetadata()
        self.params = dict(params or {})
        self.data_mat: dict[str, Any] | None = None

    @property
    def algorithm_id(self) -> str:
        return self._metadata.algorithm_id

    @property
    def metadata(self) -> PressureAlgorithmMetadata:
        return self._metadata

    def process_data(self, payload: Mapping[str, Any] | PressureInput | None = None) -> dict[str, Any]:
        pressure_input = PressureInput.from_payload(payload)
        sensors = coerce_sensors(pressure_input, default_name="pressure")
        processed = {
            "algorithm_id": self.algorithm_id,
            "sensor_type": self.sensor_type,
            "alarm_index": pressure_input.alarm_index,
            "alarm_reason": pressure_input.alarm_reason,
            "conventional_solution": pressure_input.conventional_solution,
            "sensors": sensors,
            "sensor_count": len(sensors),
            "params": {**pressure_input.params, **self.params},
            "pseudo_features": {
                "mean_pressure": first_mean(sensors),
                "max_pressure_delta": max_delta(sensors),
            },
        }
        self.data_mat = processed
        return processed

    def detect(self, data: dict[str, Any] | None = None) -> list[PressureEvent]:
        processed = data if isinstance(data, dict) else self.data_mat
        if not isinstance(processed, dict):
            return []

        params = dict(processed.get("params") or {})
        threshold = float(params.get("score_threshold", 0.02))
        max_events = int(params.get("max_events", 1))
        events: list[PressureEvent] = []
        for sensor in processed.get("sensors", []):
            values = numeric_values(sensor)
            if not values:
                continue
            baseline = mean(values)
            value = max(values, key=lambda item: abs(item - baseline))
            # Pseudo pressure logic: pressure is sensitive to relative drift.
            score = abs(value - baseline) / (abs(baseline) + 1.0)
            if score < threshold:
                continue
            events.append(
                PressureEvent(
                    name=str(sensor.get("name", "pressure")),
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
