"""Shared domain helpers for OEE_Test sub-algorithms."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from pydantic import BaseModel, Field, field_validator

OeeInputT = TypeVar("OeeInputT", bound="BaseOeeInput")


class BaseOeeInput(BaseModel):
    """Common OEE request shape for capability payloads."""

    alarm_index: str = Field(default="", description="报警点位或事件 ID。")
    alarm_reason: str = Field(default="", description="报警上下文或原因描述。")
    conventional_solution: str = Field(default="", description="传统经验处理建议。")
    sensor_name: str = Field(default="", description="单传感器输入时的传感器名称。")
    coordinate: str = Field(default="", description="传感器坐标、设备或工位信息。")
    timestamps: list[str] = Field(default_factory=list, description="传感器采样时间序列。")
    values: list[float] = Field(default_factory=list, description="单传感器输入时的采样值。")
    sensors: list[dict[str, Any]] = Field(default_factory=list, description="标准多传感器输入。")
    params: dict[str, Any] = Field(default_factory=dict, description="本次调用覆盖的算法参数。")

    @field_validator("values", mode="before")
    @classmethod
    def normalize_values(cls, value: Any) -> list[float]:
        if not isinstance(value, list | tuple):
            return []
        values: list[float] = []
        for item in value:
            try:
                values.append(float(item))
            except (TypeError, ValueError):
                continue
        return values

    @classmethod
    def from_payload(cls: type[OeeInputT], payload: Mapping[str, Any] | OeeInputT | None = None) -> OeeInputT:
        if isinstance(payload, cls):
            oee_input = payload
        else:
            body = dict(payload or {})
            body.pop("algorithm_id", None)
            oee_input = cls.from_dict(body)

        oee_input.validate_sensor_request()
        return oee_input

    @classmethod
    def from_dict(cls: type[OeeInputT], payload: Mapping[str, Any] | None = None) -> OeeInputT:
        payload = payload or {}
        sensors = payload.get("sensors", [])
        timestamps = payload.get("timestamps", [])
        body: dict[str, Any] = {
            "alarm_index": str(payload.get("alarm_index", "")),
            "alarm_reason": str(payload.get("alarm_reason", "")),
            "conventional_solution": str(payload.get("conventional_solution", "")),
            "sensor_name": str(payload.get("sensor_name") or payload.get("name") or ""),
            "coordinate": str(payload.get("coordinate", "")),
            "timestamps": [str(item) for item in timestamps] if isinstance(timestamps, list | tuple) else [],
            "values": payload.get("values", []),
            "sensors": [dict(item) for item in sensors if isinstance(item, Mapping)] if isinstance(sensors, list) else [],
        }
        if isinstance(payload.get("params"), dict):
            body["params"] = payload["params"]
        return cls(**body)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def is_valid(self) -> bool:
        return bool(self.sensors) or bool(self.values)

    def validate_sensor_request(self) -> None:
        if not self.is_valid():
            raise ValueError("invalid OEE input: sensors or values are required")


class BaseOeeOutput(BaseModel):
    """Common OEE algorithm output event."""

    name: str = Field(default="", description="异常传感器名称。")
    coordinate: str = Field(default="", description="异常位置或坐标。")
    time: str = Field(default="", description="异常时间。")
    normal: float = Field(default=0.0, description="伪基准值。")
    value: float = Field(default=0.0, description="异常采样值。")
    score: float = Field(default=0.0, description="异常分数。")
    algorithm_id: str = Field(default="", description="产生该事件的算法 ID。")
    sensor_type: str = Field(default="", description="传感器类型。")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None):
        payload = payload or {}
        return cls(
            name=str(payload.get("name", "")),
            coordinate=str(payload.get("coordinate", "")),
            time=str(payload.get("time", "")),
            normal=float(payload.get("normal", 0.0)),
            value=float(payload.get("value", 0.0)),
            score=float(payload.get("score", 0.0)),
            algorithm_id=str(payload.get("algorithm_id", "")),
            sensor_type=str(payload.get("sensor_type", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


def coerce_sensors(oee_input: BaseOeeInput, *, default_name: str) -> list[dict[str, Any]]:
    if oee_input.sensors:
        return [dict(sensor) for sensor in oee_input.sensors]
    return [
        {
            "name": oee_input.sensor_name or default_name,
            "coordinate": oee_input.coordinate,
            "timestamps": list(oee_input.timestamps),
            "values": list(oee_input.values),
        }
    ]
