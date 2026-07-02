"""State contracts for workflow orchestration."""

from __future__ import annotations

from typing import Any, TypedDict


class APCWorkflowState(TypedDict, total=False):
    """State carried by the APC adjust workflow."""

    apc_input: dict[str, Any]
    apc_result: dict[str, Any] | None
    explanation: str | None
    explanation_error: str | None
    error: dict[str, Any] | None
    trace: list[dict[str, Any]]
