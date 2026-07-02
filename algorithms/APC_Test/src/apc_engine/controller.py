"""Pseudo APC controller used by the APC_Test wheel.

This module keeps the same public shape as a real algorithm wheel:
process_data() -> control() -> adjust(). The internals are intentionally simple
so peip can validate packaging, metadata, routing, and conversion boundaries
without depending on production APC logic.
"""

from __future__ import annotations

from typing import Any

from apc_engine.domain import APCInput, APCResult


class APCEngineController:
    """Metadata-compatible APC controller with placeholder algorithm logic."""

    @property
    def algorithm_id(self) -> str:
        return "apc.test.r2r_controller"

    def process_data(self, apc_input: APCInput | None = None) -> dict[str, Any]:
        """Convert APCInput into internal pseudo features."""
        if apc_input is None:
            return {}
        
        process = apc_input.process.strip().upper()
        return {
            "target_p": apc_input.target_p,
            "p_data": dict(apc_input.p_data),
            "adj_data": dict(apc_input.adj_data),
            "machine_id": apc_input.machine_id,
            "tube_id": apc_input.tube_id,
            "adjust_max_limit": apc_input.adjust_max_limit,
            "process": process,
            "pseudo_features": {
                "sample_count": _sample_count(apc_input.p_data),
                "first_mean": _first_numeric_mean(apc_input.p_data),
            },
        }

    def control(self, data: dict[str, Any] | None = None) -> APCResult:
        """Run placeholder control logic and return an APCResult."""
        if not data:
            return APCResult(algorithm_id=self.algorithm_id)

        process = str(data.get("process", "RB")).upper()
        target_p = float(data.get("target_p", 0.0))
        limit = max(0.0, float(data.get("adjust_max_limit", 2)))
        first_mean = float((data.get("pseudo_features") or {}).get("first_mean", target_p))

        # Pseudo logic: drive the observed mean toward target_p with clamping.
        delta = _clamp((target_p - first_mean) * 0.01, -limit, limit)
        temperature = [round(delta * (1 + idx * 0.05), 4) for idx in range(6)]

        adjustments: dict[str, list[float]] = {"temperature": temperature}
        if process == "LP":
            adjustments["flow"] = [round(delta * 0.25, 4) for _ in range(3)]

        blocked_by_actuator = {
            name: [idx + 1 for idx, value in enumerate(values) if abs(value) >= limit and limit > 0]
            for name, values in adjustments.items()
        }
        blocked_by_actuator = {name: zones for name, zones in blocked_by_actuator.items() if zones}
        blocked_zones = sorted({zone for zones in blocked_by_actuator.values() for zone in zones})

        return APCResult(
            adjustments=adjustments,
            warning=bool(blocked_by_actuator),
            blocked_zones=blocked_zones,
            blocked_by_actuator=blocked_by_actuator,
            algorithm_id=self.algorithm_id,
        )

    def adjust(self, apc_input: APCInput | None = None) -> APCResult:
        """Execute a complete pseudo APC adjustment."""
        return self.control(self.process_data(apc_input))


def _sample_count(p_data: dict[str, Any]) -> int:
    for value in p_data.values():
        if isinstance(value, (list, tuple)):
            return len(value)
    return 1 if p_data else 0


def _first_numeric_mean(p_data: dict[str, Any]) -> float:
    for value in p_data.values():
        values = value if isinstance(value, (list, tuple)) else [value]
        numeric_values: list[float] = []
        for item in values:
            try:
                numeric_values.append(float(item))
            except (TypeError, ValueError):
                continue
        if numeric_values:
            return sum(numeric_values) / len(numeric_values)
    return 0.0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
