"""Minimal aggregate routing definitions for OEE_Test."""

from __future__ import annotations

ALGORITHM_CONTROLLERS = {
    "oee.temperature_detector": "oee_engine.temperature.TemperatureController",
    "oee.pressure_detector": "oee_engine.pressure.PressureController",
}


def get_class_path(algorithm_id: str) -> str:
    class_path = ALGORITHM_CONTROLLERS.get(algorithm_id)
    if class_path is None:
        raise ValueError(
            f"unknown OEE_Test sensor analysis algorithm_id: {algorithm_id!r}; "
            f"supported: {', '.join(get_supported_algorithms())}"
        )
    return class_path


def get_supported_algorithms() -> list[str]:
    return sorted(ALGORITHM_CONTROLLERS)
