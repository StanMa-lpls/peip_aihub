"""Workflow API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.service import get_algorithm_registry
from app.api.models.algorithm_model import ResponseModel
from app.api.models.workflow_model import (
    APCAdjustWorkflowRequest,
    apc_workflow_request_to_payload,
)
from app.common import response
from app.workflows.runner import WorkflowExecutionError, run_apc_adjust_workflow

workflow_router = APIRouter(prefix="/workflows", tags=["Workflows"])


@workflow_router.post(
    "/apc/adjust",
    summary="Run APC adjust workflow",
    response_model=ResponseModel,
)
async def run_apc_adjust_workflow_api(
    request: APCAdjustWorkflowRequest,
    registry: AlgorithmRegistry = Depends(get_algorithm_registry),
) -> ResponseModel:
    """Run APC adjust capability, then explain the result with local Ollama."""

    try:
        data = run_apc_adjust_workflow(
            apc_workflow_request_to_payload(request),
            registry=registry,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Workflow input validation failed",
                "data": {"error": f"ValueError: {exc}"},
            },
        ) from exc
    except WorkflowExecutionError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Workflow execution failed",
                "data": {"error": exc.error},
            },
        ) from exc
    return await response.success(data=data)
