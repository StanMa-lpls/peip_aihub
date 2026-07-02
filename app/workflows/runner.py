"""Workflow runner helpers."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.algorithms.registry import AlgorithmRegistry
from app.core.settings import OllamaSettings
from app.workflows.graphs.apc_adjust import build_apc_adjust_graph


class WorkflowExecutionError(RuntimeError):
    """Raised when a workflow node fails before a normal result is available."""

    def __init__(self, error: dict[str, Any], state: dict[str, Any]) -> None:
        super().__init__(str(error.get("message") or error))
        self.error = error
        self.state = state


def run_apc_adjust_workflow(
    apc_input: dict[str, Any],
    *,
    registry: AlgorithmRegistry | None = None,
    llm: Any | None = None,
    ollama_config: OllamaSettings | None = None,
) -> dict[str, Any]:
    """Run the APC adjust workflow and return API-ready data."""

    started = perf_counter()
    graph = build_apc_adjust_graph(
        registry=registry,
        llm=llm,
        ollama_config=ollama_config,
    )
    state = graph.invoke(
        {
            "apc_input": dict(apc_input),
            "apc_result": None,
            "explanation": None,
            "explanation_error": None,
            "error": None,
            "trace": [],
        }
    )
    elapsed_seconds = perf_counter() - started

    if state.get("error"):
        raise WorkflowExecutionError(state["error"], dict(state))

    return {
        "explanation": state.get("explanation"),
        "explanation_error": state.get("explanation_error"),
        "apc_result": state.get("apc_result"),
        "trace": state.get("trace") or [],
        "elapsed_seconds": elapsed_seconds,
    }
