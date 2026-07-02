"""LLM explanation node for APC workflow results."""

from __future__ import annotations

import json
from collections.abc import Callable
from time import perf_counter
from typing import Any

from app.core.settings import OllamaSettings
from app.workflows.llm.ollama import create_ollama_chat_model, message_content_to_text
from app.workflows.state import APCWorkflowState


def make_llm_explain_node(
    *,
    llm: Any | None = None,
    ollama_config: OllamaSettings | None = None,
) -> Callable[[APCWorkflowState], dict[str, Any]]:
    """Build a node that explains APC output using the local Ollama LLM."""

    active_llm = llm

    def llm_explain_node(state: APCWorkflowState) -> dict[str, Any]:
        nonlocal active_llm

        started = perf_counter()
        trace = _trace(state)
        apc_result = state.get("apc_result")
        if apc_result is None:
            error = {
                "type": "MissingAPCResult",
                "message": "APC result is required before LLM explanation.",
                "node": "llm_explain",
            }
            return {
                "explanation_error": error["message"],
                "trace": [
                    *trace,
                    {
                        "node": "llm_explain",
                        "result": "error",
                        "elapsed_ms": (perf_counter() - started) * 1000,
                        "error": error,
                    },
                ],
            }

        try:
            if active_llm is None:
                active_llm = create_ollama_chat_model(ollama_config)
            message = active_llm.invoke(
                build_explain_prompt(state.get("apc_input") or {}, apc_result)
            )
            explanation = message_content_to_text(message)
        except Exception as exc:
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "node": "llm_explain",
            }
            return {
                "explanation_error": str(exc),
                "trace": [
                    *trace,
                    {
                        "node": "llm_explain",
                        "result": "error",
                        "elapsed_ms": (perf_counter() - started) * 1000,
                        "error": error,
                    },
                ],
            }

        return {
            "explanation": explanation,
            "trace": [
                *trace,
                {
                    "node": "llm_explain",
                    "result": "success",
                    "elapsed_ms": (perf_counter() - started) * 1000,
                },
            ],
        }

    return llm_explain_node


def build_explain_prompt(apc_input: dict[str, Any], apc_result: dict[str, Any]) -> str:
    """Build the deterministic prompt used to explain APC output."""

    return (
        "你是 APC Run-to-Run 控制结果解释助手。请基于算法输入和算法输出，"
        "用中文解释本次调整建议、是否有 warning、blocked_zones 的含义，以及使用注意事项。"
        "不要重新计算调整量，不要修改算法输出。\n\n"
        "APC 输入：\n"
        f"{_to_pretty_json(apc_input)}\n\n"
        "APC 算法输出：\n"
        f"{_to_pretty_json(apc_result)}"
    )


def _to_pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _trace(state: APCWorkflowState) -> list[dict[str, Any]]:
    return list(state.get("trace") or [])
