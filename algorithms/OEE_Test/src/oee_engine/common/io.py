"""Shared input/output helpers for OEE_Test sub-algorithms."""

from __future__ import annotations

from typing import Any, Mapping, TypeVar

from pydantic import BaseModel, Field, field_validator

SensorInputT = TypeVar("SensorInputT", bound="BaseSensorInput")


class BaseSensorInput(BaseModel):
    """Common sensor-analysis request shape for capability payloads."""

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
    def from_payload(cls: type[SensorInputT], payload: Mapping[str, Any] | SensorInputT | None = None) -> SensorInputT:
        if isinstance(payload, cls):
            sensor_input = payload
        else:
            body = dict(payload or {})
            body.pop("algorithm_id", None)
            sensor_input = cls.from_dict(body)

        sensor_input.validate_sensor_request()
        return sensor_input

    @classmethod
    def from_dict(cls: type[SensorInputT], payload: Mapping[str, Any] | None = None) -> SensorInputT:
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
            raise ValueError("invalid OEE sensor input: sensors or values are required")


class BaseSensorEvent(BaseModel):
    """Common OEE sensor anomaly event."""

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


def coerce_sensors(sensor_input: BaseSensorInput, *, default_name: str) -> list[dict[str, Any]]:
    if sensor_input.sensors:
        return [dict(sensor) for sensor in sensor_input.sensors]
    return [
        {
            "name": sensor_input.sensor_name or default_name,
            "coordinate": sensor_input.coordinate,
            "timestamps": list(sensor_input.timestamps),
            "values": list(sensor_input.values),
        }
    ]


def to_jsonable(value: Any) -> Any:
    """Convert detector return values into JSON-friendly structures."""

    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_jsonable(value.to_dict())
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return to_jsonable(value.model_dump())
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return to_jsonable(vars(value))
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
