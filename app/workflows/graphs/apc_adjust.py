"""LangGraph definition for the APC adjust workflow."""

from __future__ import annotations

from typing import Any

from app.algorithms.registry import AlgorithmRegistry
from app.core.settings import OllamaSettings
from app.workflows.nodes.apc import make_apc_algorithm_node
from app.workflows.nodes.explain import make_llm_explain_node
from app.workflows.state import APCWorkflowState


def build_apc_adjust_graph(
    *,
    registry: AlgorithmRegistry | None = None,
    llm: Any | None = None,
    ollama_config: OllamaSettings | None = None,
) -> Any:
    """Build and compile the deterministic APC adjust graph."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("请先安装 langgraph 依赖：python -m pip install langgraph") from exc

    graph = StateGraph(APCWorkflowState)
    graph.add_node("apc_algorithm", make_apc_algorithm_node(registry=registry))
    graph.add_node("llm_explain", make_llm_explain_node(llm=llm, ollama_config=ollama_config))
    graph.add_edge(START, "apc_algorithm")
    graph.add_conditional_edges(
        "apc_algorithm",
        _route_after_apc,
        {
            "llm_explain": "llm_explain",
            END: END,
        },
    )
    graph.add_edge("llm_explain", END)
    return graph.compile()


def _route_after_apc(state: APCWorkflowState) -> str:
    if state.get("error"):
        try:
            from langgraph.graph import END
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("请先安装 langgraph 依赖：python -m pip install langgraph") from exc
        return END
    return "llm_explain"
