"""Pressure input and output models for OEE_Test."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import Field

from oee_engine.common import BaseSensorEvent, BaseSensorInput


class PressureInput(BaseSensorInput):
    """One pressure anomaly detection request."""

    params: dict[str, Any] = Field(
        default_factory=lambda: {
            "score_threshold": 0.02,
            "max_events": 1,
        },
        description="压力伪检测参数；配置或 payload 可覆盖。",
    )

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any] | "PressureInput" | None = None,
    ) -> "PressureInput":
        return super().from_payload(payload)


class PressureEvent(BaseSensorEvent):
    """One pressure anomaly event."""

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None) -> "PressureEvent":
        event = super().from_dict(payload)
        return cls(**event.to_dict())
