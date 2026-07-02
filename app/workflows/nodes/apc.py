"""APC workflow nodes."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from app.algorithms.exceptions import (
    AlgorithmInvocationError,
    AlgorithmLoadError,
    AlgorithmNotFoundError,
)
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.service import call_algorithm_capability
from app.workflows.state import APCWorkflowState

APC_ALGORITHM_ID = "apc.r2r_controller"
APC_ADJUST_CAPABILITY = "adjust"


def make_apc_algorithm_node(
    *,
    registry: AlgorithmRegistry | None = None,
) -> Callable[[APCWorkflowState], dict[str, Any]]:
    """Build a LangGraph node that executes the APC adjust capability."""

    def apc_algorithm_node(state: APCWorkflowState) -> dict[str, Any]:
        started = perf_counter()
        trace = _trace(state)
        payload = dict(state.get("apc_input") or {})

        try:
            result = call_algorithm_capability(
                APC_ALGORITHM_ID,
                APC_ADJUST_CAPABILITY,
                payload,
                registry=registry,
            )
        except (AlgorithmInvocationError, AlgorithmLoadError, AlgorithmNotFoundError) as exc:
            elapsed_ms = (perf_counter() - started) * 1000
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "node": "apc_algorithm",
            }
            return {
                "error": error,
                "trace": [
                    *trace,
                    {
                        "node": "apc_algorithm",
                        "result": "error",
                        "elapsed_ms": elapsed_ms,
                        "error": error,
                    },
                ],
            }

        elapsed_ms = (perf_counter() - started) * 1000
        return {
            "apc_result": result,
            "trace": [
                *trace,
                {
                    "node": "apc_algorithm",
                    "result": "success",
                    "elapsed_ms": elapsed_ms,
                },
            ],
        }

    return apc_algorithm_node


def _trace(state: APCWorkflowState) -> list[dict[str, Any]]:
    return list(state.get("trace") or [])
