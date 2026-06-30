"""Temperature input and output models for OEE_Test."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import Field

from oee_engine.common import BaseSensorEvent, BaseSensorInput


class TemperatureInput(BaseSensorInput):
    """One temperature anomaly detection request."""

    params: dict[str, Any] = Field(
        default_factory=lambda: {
            "score_threshold": 0.3,
            "max_events": 3,
        },
        description="温度伪检测参数；配置或 payload 可覆盖。",
    )

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any] | "TemperatureInput" | None = None,
    ) -> "TemperatureInput":
        return super().from_payload(payload)


class TemperatureEvent(BaseSensorEvent):
    """One temperature anomaly event."""

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None) -> "TemperatureEvent":
        event = super().from_dict(payload)
        return cls(**event.to_dict())
