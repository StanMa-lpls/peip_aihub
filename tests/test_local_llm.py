"""本地 Ollama LLM 连通性与 Tool Call 测试（Streamlit UI）。

Run:
    streamlit run tests/test_local_llm.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

import httpx
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_BASE_URL = "http://172.30.191.74:11434"
DEFAULT_MODEL = "gemma4:e2b"
DEFAULT_TOOL_PROMPT = "23.1111 和 45.89 相加，再把得到的和乘以 3.123，最后告诉我最终结果。"
REQUEST_TIMEOUT_SECONDS = 120.0
MAX_TOOL_ROUNDS = 5

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "计算两个数的加法，返回 a + b。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个加数"},
                    "b": {"type": "number", "description": "第二个加数"},
                },
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "计算两个数的乘法，返回 a × b。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个乘数"},
                    "b": {"type": "number", "description": "第二个乘数"},
                },
                "required": ["a", "b"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "你是一个数学助手。遇到加减乘除计算时，必须调用提供的工具完成运算，"
    "不要心算或编造结果。若需要多步计算，请依次调用工具并在获得工具结果后给出最终答案。"
)


@dataclass
class ToolExecutionRecord:
    round_index: int
    call_index: int
    name: str
    arguments: dict[str, Any]
    result: str
    success: bool
    error: str | None = None
    elapsed_ms: float = 0.0


@dataclass
class ToolCallRound:
    round_index: int
    assistant_message: dict[str, Any]
    raw_response: dict[str, Any]
    executions: list[ToolExecutionRecord] = field(default_factory=list)


@dataclass
class ToolCallTrace:
    messages: list[dict[str, Any]]
    rounds: list[ToolCallRound]
    final_content: str
    final_response: dict[str, Any] | None
    total_elapsed: float
    api_responses: list[dict[str, Any]] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_output_tokens: int = 0


def _chat_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/chat"


def _generate_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/generate"


def add(a: float, b: float) -> float:
    return float(a) + float(b)


def multiply(a: float, b: float) -> float:
    return float(a) * float(b)


TOOL_REGISTRY: dict[str, Callable[..., float]] = {
    "add": add,
    "multiply": multiply,
}


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    raise TypeError(f"无法解析 tool arguments: {type(raw).__name__}")


def _coerce_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise TypeError(f"参数必须是数字，收到: {value!r}")


def execute_tool(name: str, arguments: dict[str, Any]) -> tuple[str, bool, str | None]:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return "", False, f"未知工具: {name}"

    try:
        parsed = _parse_arguments(arguments)
        if name in {"add", "multiply"}:
            result = fn(_coerce_number(parsed["a"]), _coerce_number(parsed["b"]))
        else:
            result = fn(**parsed)
        return str(result), True, None
    except Exception as exc:
        return "", False, f"{type(exc).__name__}: {exc}"


def chat_once(
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    response = httpx.post(
        _chat_url(base_url),
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _extract_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls = message.get("tool_calls") or []
    normalized: list[dict[str, Any]] = []
    for item in tool_calls:
        fn = item.get("function") or {}
        name = fn.get("name", "")
        arguments = _parse_arguments(fn.get("arguments") or {})
        normalized.append({"name": name, "arguments": arguments, "raw": item})
    return normalized


def run_tool_call_loop(
    base_url: str,
    model: str,
    user_prompt: str,
) -> ToolCallTrace:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    rounds: list[ToolCallRound] = []
    api_responses: list[dict[str, Any]] = []
    started = time.perf_counter()
    final_response: dict[str, Any] | None = None
    final_content = ""

    for round_index in range(1, MAX_TOOL_ROUNDS + 1):
        raw = chat_once(base_url, model, messages, tools=TOOL_DEFINITIONS)
        api_responses.append(raw)
        message = raw.get("message") or {}
        final_response = raw

        tool_calls = _extract_tool_calls(message)
        if not tool_calls:
            final_content = (message.get("content") or "").strip()
            break

        round_record = ToolCallRound(
            round_index=round_index,
            assistant_message=message,
            raw_response=raw,
        )
        messages.append(message)

        for call_index, call in enumerate(tool_calls, start=1):
            exec_started = time.perf_counter()
            result, success, error = execute_tool(call["name"], call["arguments"])
            elapsed_ms = (time.perf_counter() - exec_started) * 1000

            round_record.executions.append(
                ToolExecutionRecord(
                    round_index=round_index,
                    call_index=call_index,
                    name=call["name"],
                    arguments=call["arguments"],
                    result=result,
                    success=success,
                    error=error,
                    elapsed_ms=elapsed_ms,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_name": call["name"],
                    "content": result if success else f"ERROR: {error}",
                }
            )

        rounds.append(round_record)
    else:
        final_content = "(已达最大 tool 调用轮次，未获得最终文本回复)"

    total_prompt_tokens = sum(
        int(r.get("prompt_eval_count") or 0) for r in api_responses
    )
    total_output_tokens = sum(int(r.get("eval_count") or 0) for r in api_responses)

    return ToolCallTrace(
        messages=messages,
        rounds=rounds,
        final_content=final_content,
        final_response=final_response,
        total_elapsed=time.perf_counter() - started,
        api_responses=api_responses,
        total_prompt_tokens=total_prompt_tokens,
        total_output_tokens=total_output_tokens,
    )


def generate_once(base_url: str, model: str, prompt: str) -> dict[str, Any]:
    response = httpx.post(
        _generate_url(base_url),
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def generate_stream(
    base_url: str, model: str, prompt: str
) -> Iterator[tuple[str, dict[str, Any] | None]]:
    with httpx.stream(
        "POST",
        _generate_url(base_url),
        json={"model": model, "prompt": prompt, "stream": True},
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            payload = json.loads(line)
            chunk = payload.get("response", "")
            if payload.get("done"):
                yield chunk, payload
                return
            yield chunk, None


def list_models(base_url: str) -> list[str]:
    response = httpx.get(
        f"{base_url.rstrip('/')}/api/tags",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    models = response.json().get("models", [])
    return [item.get("name", "") for item in models if item.get("name")]


def _format_duration_ns(ns: int | float | None) -> str:
    if not ns:
        return "-"
    return f"{float(ns) / 1e9:.2f}s"


def _render_metrics(payload: dict[str, Any] | None, elapsed: float) -> None:
    cols = st.columns(4)
    cols[0].metric("总耗时", f"{elapsed:.2f}s")
    if not payload:
        cols[1].metric("模型加载", "-")
        cols[2].metric("Prompt tokens", "-")
        cols[3].metric("生成 tokens", "-")
        return
    cols[1].metric("模型加载", _format_duration_ns(payload.get("load_duration")))
    cols[2].metric("Prompt tokens", str(payload.get("prompt_eval_count", "-")))
    cols[3].metric("生成 tokens", str(payload.get("eval_count", "-")))


def _render_tool_metrics(trace: ToolCallTrace) -> None:
    cols = st.columns(4)
    cols[0].metric("总耗时", f"{trace.total_elapsed:.2f}s")
    cols[1].metric("API 调用轮次", len(trace.api_responses))
    cols[2].metric("Prompt tokens (合计)", trace.total_prompt_tokens)
    cols[3].metric("Output tokens (合计)", trace.total_output_tokens)

    if len(trace.api_responses) > 1:
        with st.expander("各轮次 token 明细"):
            rows = []
            for index, response in enumerate(trace.api_responses, start=1):
                rows.append(
                    {
                        "轮次": index,
                        "Prompt tokens": response.get("prompt_eval_count", 0),
                        "Output tokens": response.get("eval_count", 0),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_tool_definitions() -> None:
    with st.expander("已注册工具 (add / multiply)", expanded=False):
        for tool in TOOL_DEFINITIONS:
            fn = tool["function"]
            st.markdown(f"**{fn['name']}** — {fn['description']}")
            st.json(fn["parameters"])


def _render_tool_trace(trace: ToolCallTrace) -> None:
    st.subheader("Tool Call 追踪")
    summary_cols = st.columns(4)
    total_calls = sum(len(r.executions) for r in trace.rounds)
    success_calls = sum(
        1 for r in trace.rounds for e in r.executions if e.success
    )
    summary_cols[0].metric("调用轮次", len(trace.rounds))
    summary_cols[1].metric("Tool 调用次数", total_calls)
    summary_cols[2].metric("成功执行", success_calls)
    summary_cols[3].metric(
        "失败",
        total_calls - success_calls,
        delta=None if success_calls == total_calls else -(total_calls - success_calls),
    )

    if not trace.rounds:
        st.info("模型未返回 tool_calls，可能直接给出了文本回复。")
        return

    for round_record in trace.rounds:
        st.markdown(f"#### 第 {round_record.round_index} 轮 — 模型请求调用工具")
        with st.container(border=True):
            st.caption("Assistant 消息（含 tool_calls）")
            st.json(round_record.assistant_message)

            for execution in round_record.executions:
                status = "✅" if execution.success else "❌"
                st.markdown(
                    f"**{status} 调用 #{execution.call_index}: `{execution.name}`** "
                    f"({execution.elapsed_ms:.1f} ms)"
                )
                arg_cols = st.columns(2)
                with arg_cols[0]:
                    st.markdown("**参数**")
                    st.json(execution.arguments)
                with arg_cols[1]:
                    st.markdown("**执行结果**")
                    if execution.success:
                        st.success(execution.result)
                    else:
                        st.error(execution.error or "未知错误")

            with st.expander("本轮原始 API 响应"):
                st.json(round_record.raw_response)

    with st.expander("完整 messages 历史（含 tool 回传）"):
        st.json(trace.messages)


def _clear_session() -> None:
    for key in (
        "last_response",
        "last_metrics",
        "last_tool_trace",
        "last_mode",
    ):
        st.session_state.pop(key, None)


def main() -> None:
    st.set_page_config(page_title="本地 LLM 测试", page_icon="🤖", layout="wide")
    st.title("本地 Ollama LLM 测试")
    st.caption(
        "支持 `/api/generate` 纯文本测试，以及 `/api/chat` + tools 的 function calling 测试。"
    )

    with st.sidebar:
        st.header("连接配置")
        base_url = st.text_input("Ollama 地址", value=DEFAULT_BASE_URL)
        cached_models = st.session_state.get("ollama_models")
        if cached_models:
            picked = st.selectbox("已安装模型", ["(手动输入)"] + cached_models)
            if picked != "(手动输入)":
                model = picked
            else:
                model = st.text_input("模型名称", value=DEFAULT_MODEL, key="model_manual")
        else:
            model = st.text_input("模型名称", value=DEFAULT_MODEL)

        mode = st.radio(
            "测试模式",
            ["Tool Call 测试 (/api/chat)", "纯文本 (/api/generate)"],
        )
        tool_mode = mode.startswith("Tool Call")

        if not tool_mode:
            use_stream = st.radio("输出模式", ["流式 (stream=true)", "非流式 (stream=false)"])
            stream_enabled = use_stream.startswith("流式")
        else:
            stream_enabled = False
            st.info("Tool Call 模式使用非流式 `/api/chat`。")

        if st.button("刷新模型列表", use_container_width=True):
            try:
                names = list_models(base_url)
                st.session_state["ollama_models"] = names
                st.success(f"已获取 {len(names)} 个模型")
            except Exception as exc:
                st.error(f"获取模型列表失败: {exc}")

        if tool_mode:
            _render_tool_definitions()

    default_prompt = DEFAULT_TOOL_PROMPT if tool_mode else "23.1111 和 45.89 相加，再把得到的和乘以 3.123，最后告诉我最终结果。"
    prompt = st.text_area(
        "Prompt",
        value=default_prompt,
        height=120,
        placeholder="输入要发送给模型的提示词",
    )

    col_send, col_clear = st.columns([1, 5])
    send = col_send.button("发送", type="primary", use_container_width=True)
    if col_clear.button("清空回复", use_container_width=True):
        _clear_session()
        st.rerun()

    if not send:
        if trace := st.session_state.get("last_tool_trace"):
            if st.session_state.get("last_mode") == "tool":
                st.subheader("最终回复")
                st.markdown(trace.final_content or "_(空)_")
                _render_tool_trace(trace)
                _render_tool_metrics(trace)
                return

        if last := st.session_state.get("last_response"):
            st.subheader("回复")
            st.markdown(last)
            if metrics := st.session_state.get("last_metrics"):
                _render_metrics(metrics["payload"], metrics["elapsed"])
        return

    if not prompt.strip():
        st.warning("请输入 Prompt")
        return

    started = time.perf_counter()
    try:
        if tool_mode:
            with st.spinner("模型推理与工具执行中..."):
                trace = run_tool_call_loop(base_url, model, prompt.strip())

            st.session_state["last_tool_trace"] = trace
            st.session_state["last_mode"] = "tool"
            st.session_state.pop("last_response", None)
            st.session_state.pop("last_metrics", None)

            st.subheader("最终回复")
            st.markdown(trace.final_content or "_(空)_")
            _render_tool_trace(trace)
            _render_tool_metrics(trace)
            return

        st.session_state.pop("last_tool_trace", None)
        st.session_state["last_mode"] = "generate"

        if stream_enabled:
            placeholder = st.empty()
            chunks: list[str] = []
            final_payload: dict[str, Any] | None = None

            for chunk, payload in generate_stream(base_url, model, prompt):
                if chunk:
                    chunks.append(chunk)
                    placeholder.markdown("".join(chunks))
                if payload is not None:
                    final_payload = payload

            elapsed = time.perf_counter() - started
            full_text = "".join(chunks)
            st.session_state["last_response"] = full_text
            if final_payload:
                st.session_state["last_metrics"] = {
                    "payload": final_payload,
                    "elapsed": elapsed,
                }
                with st.expander("原始响应 (最后一帧)"):
                    st.json(final_payload)
                _render_metrics(final_payload, elapsed)
        else:
            with st.spinner("模型生成中..."):
                payload = generate_once(base_url, model, prompt)
            elapsed = time.perf_counter() - started
            full_text = payload.get("response", "")
            st.session_state["last_response"] = full_text

            st.subheader("回复")
            st.markdown(full_text)
            st.session_state["last_metrics"] = {"payload": payload, "elapsed": elapsed}
            with st.expander("原始响应"):
                st.json(payload)
            _render_metrics(payload, elapsed)

    except httpx.HTTPStatusError as exc:
        st.error(f"HTTP {exc.response.status_code}: {exc.response.text[:500]}")
    except httpx.RequestError as exc:
        st.error(f"请求失败: {exc}")
    except Exception as exc:
        st.error(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
