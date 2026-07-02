"""APC input and output models for the APC_Test wheel.

These models are the algorithm package's source of truth. A peip adapter should
reuse them directly instead of redefining shadow APCInput/APCResult classes.
"""

from __future__ import annotations

from platform import mac_ver
from typing import Any, Mapping

from pydantic import BaseModel, Field, field_validator


class APCInput(BaseModel):
    """One Run-to-Run APC adjustment request."""

    machine_id: str = Field(
        description="机台编号，用于定位 APC 模型与工艺数据来源。",
        examples=["M01"],
        
    )
    tube_id: str = Field(
        description="管号/炉管编号，用于区分同一机台下的不同工艺腔体。",
        examples=["T01"],
    )
    target_p: float = Field(
        description="目标方阻或目标工艺指标，必须大于 0 才视为有效 APC 请求。",
        examples=[100.0],
    )
    p_data: dict[str, Any] = Field(
        default_factory=dict,
        description="当前批次工艺测量数据，通常为列名到序列值的映射。",
        examples=[{"p1_mean": [96.0, 97.0, 98.0], "Time": ["t1", "t2", "t3"]}],
    )
    adj_data: dict[str, Any] = Field(
        default_factory=dict,
        description="历史调整记录，算法可用其判断连续调整和限幅策略。",
        examples=[{"temperature": [0.0, 0.0, 0.0]}],
    )
    adjust_max_limit: int = Field(
        default=2,
        description="单次调整最大限幅。",
        lt=3,
        gt=1,
        examples=[2],
    )
    process: str = Field(
        default="RB",
        description="本次 APC 请求的工艺类型，例如 RB 或 LP；算法会按该字段选择对应工序逻辑。",
        examples=["RB"],
    )

    @field_validator("machine_id", mode="before")
    @classmethod
    def validate_machine_id(cls, value: Any) -> str:
        machine_id = str(value or "").strip().upper()
        if machine_id not in ["M01", "M02", "M03"]:
            raise ValueError("invalid APC input: machine_id must be M01, M02 or M03")
        return machine_id


    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any] | "APCInput" | None = None,
    ) -> "APCInput":
        if isinstance(payload, cls):
            apc_input = payload
        else:
            body = dict(payload or {})
            body.pop("algorithm_id", None)
            apc_input = cls.from_dict(body)

        apc_input.validate_apc_request()
        return apc_input

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None = None) -> "APCInput":
        payload = payload or {}
        return cls(
            machine_id=str(payload.get("machine_id", "")),
            tube_id=str(payload.get("tube_id", "")),
            target_p=float(payload.get("target_p", 0.0)),
            p_data=payload.get("p_data", {}) if isinstance(payload.get("p_data", {}), dict) else {},
            adj_data=payload.get("adj_data", {}) if isinstance(payload.get("adj_data", {}), dict) else {},
            adjust_max_limit=int(payload.get("adjust_max_limit", 2)),
            process=str(payload.get("process", "RB")).upper(),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def validate_apc_request(self) -> None:
        if (
            not self.machine_id.strip()
            or not self.tube_id.strip()
            or self.target_p <= 0
            or self.process not in ["RB", "LP"]
        ):
            raise ValueError("invalid APC input: machine_id, tube_id, positive target_p and process RB/LP are required")


class APCResult(BaseModel):
    """One APC adjustment result.

    The dict form supports multiple actuator groups, e.g. temperature and flow.
    Bare list adjustments are still accepted for compatibility and are mapped to
    the temperature actuator.
    """

    adjustments: dict[str, list[float]] = Field(
        default_factory=lambda: {"temperature": [0.0] * 6},
        description="按 actuator 分组的调整量，例如 temperature 或 flow。",
        examples=[{"temperature": [0.03, 0.0315, 0.033, 0.0345, 0.036, 0.0375]}],
    )
    warning: bool = Field(
        default=False,
        description="是否触发限幅、熔断或其他控制预警。",
        examples=[False],
    )
    blocked_zones: list[int] = Field(
        default_factory=list,
        description="兼容旧格式的阻断通道扁平列表。",
        examples=[[]],
    )
    blocked_by_actuator: dict[str, list[int]] = Field(
        default_factory=dict,
        description="按 actuator 分组的阻断通道。",
        examples=[{"temperature": [1, 3]}],
    )
    algorithm_id: str = Field(
        default="apc.test.r2r_controller",
        description="产生该结果的算法 ID。",
        examples=["apc.r2r_controller"],
    )

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None = None) -> "APCResult":
        payload = payload or {}
        raw_adjustments = payload.get("adjustments", {"temperature": [0.0] * 6})
        if isinstance(raw_adjustments, dict):
            adjustments = {
                str(name): [float(value) for value in (values or [])]
                for name, values in raw_adjustments.items()
            }
        else:
            adjustments = {"temperature": [float(value) for value in raw_adjustments]}
        if not adjustments or not any(adjustments.values()):
            adjustments = {"temperature": [0.0] * 6}

        raw_blocked = payload.get("blocked_by_actuator", {})
        blocked_by_actuator = (
            {
                str(name): [int(zone) for zone in (zones or [])]
                for name, zones in raw_blocked.items()
            }
            if isinstance(raw_blocked, dict)
            else {}
        )
        blocked_zones = [int(zone) for zone in payload.get("blocked_zones", [])]
        if not blocked_zones and blocked_by_actuator:
            blocked_zones = sorted({zone for zones in blocked_by_actuator.values() for zone in zones})

        return cls(
            adjustments=adjustments,
            warning=bool(payload.get("warning", False)),
            blocked_zones=blocked_zones,
            blocked_by_actuator=blocked_by_actuator,
            algorithm_id=str(payload.get("algorithm_id", "apc.test.r2r_controller")),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
