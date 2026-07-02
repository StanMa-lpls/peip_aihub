"""Pydantic models for workflow APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


try:
    from apc_engine import APCInput as APCAdjustWorkflowRequest
except ImportError:

    class APCAdjustWorkflowRequest(BaseModel):
        """Fallback request model used when APCInput is not importable."""

        machine_id: str = Field(..., description="机台编号")
        tube_id: str = Field(..., description="管号/炉管编号")
        target_p: float = Field(..., gt=0, description="目标方阻或目标工艺指标")
        p_data: dict[str, Any] = Field(..., description="当前批次工艺测量数据")
        adj_data: dict[str, Any] = Field(default_factory=dict, description="历史调整记录")
        adjust_max_limit: int = Field(default=2, description="单次调整最大限幅")
        process: str = Field(default="RB", description="工艺类型，例如 RB 或 LP")


def apc_workflow_request_to_payload(request: APCAdjustWorkflowRequest) -> dict[str, Any]:
    """Return a JSON-friendly APC payload from either APCInput or fallback model."""

    from_payload = getattr(type(request), "from_payload", None)
    if callable(from_payload):
        request = from_payload(request)

    to_dict = getattr(request, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    return request.model_dump()


class APCAdjustWorkflowData(BaseModel):
    """Workflow response payload wrapped by the common ResponseModel."""

    explanation: str | None = None
    explanation_error: str | None = None
    apc_result: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
    elapsed_seconds: float
