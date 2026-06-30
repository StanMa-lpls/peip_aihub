"""Shared pseudo-scoring helpers for OEE_Test sub-algorithms."""

from __future__ import annotations

from statistics import mean
from typing import Any, Mapping


def numeric_values(sensor: Mapping[str, Any]) -> list[float]:
    values = sensor.get("values", [])
    if not isinstance(values, list | tuple):
        return []
    numeric: list[float] = []
    for item in values:
        try:
            numeric.append(float(item))
        except (TypeError, ValueError):
            continue
    return numeric


def first_mean(sensors: list[dict[str, Any]]) -> float:
    for sensor in sensors:
        values = numeric_values(sensor)
        if values:
            return float(mean(values))
    return 0.0


def max_delta(sensors: list[dict[str, Any]]) -> float:
    deltas: list[float] = []
    for sensor in sensors:
        values = numeric_values(sensor)
        if values:
            baseline = mean(values)
            deltas.append(max(abs(value - baseline) for value in values))
    return max(deltas, default=0.0)


def max_range(sensors: list[dict[str, Any]]) -> float:
    ranges: list[float] = []
    for sensor in sensors:
        values = numeric_values(sensor)
        if values:
            ranges.append(max(values) - min(values))
    return max(ranges, default=0.0)


def first_timestamp(sensor: Mapping[str, Any]) -> str:
    timestamps = sensor.get("timestamps", [])
    if isinstance(timestamps, list | tuple) and timestamps:
        return str(timestamps[0])
    return ""
