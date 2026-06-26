"""Manual LLM connectivity test.

Run:
    python tests/llm_test.py
"""

from __future__ import annotations

from pathlib import Path
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import LLMSettings

REQUEST_TIMEOUT_SECONDS = 60.0


def build_client(settings: LLMSettings):
    settings.validate()
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("请先安装 openai 依赖：python -m pip install openai") from exc
    return OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )


def call_model(client, model: str, prompt: str) -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        top_p=0.2,
        max_tokens=100,
        # extra_body={"chat_template_kwargs": {"thinking": False}},
        stream=False,
    )
    content = completion.choices[0].message.content
    return content or ""


def main() -> None:
    env_file = Path(__file__).resolve().parents[1] / "configs" / ".env"
    settings = LLMSettings.from_env(env_file)
    client = build_client(settings)

    prompt = "请只回复 OK，用于模型连通性测试。"
    for alias, model in settings.models.items():
        print(f"Testing {alias} ({model})...", flush=True)
        started = perf_counter()
        try:
            content = call_model(client, model, prompt)
        except Exception as exc:
            elapsed = perf_counter() - started
            print(f"[FAIL] {alias} ({model}) {elapsed:.2f}s: {type(exc).__name__}: {exc}")
            continue
        elapsed = perf_counter() - started
        preview = content.replace("\n", " ").strip()[:120]
        print(f"[OK] {alias} ({model}) {elapsed:.2f}s: {preview}")


if __name__ == "__main__":
    main()

    