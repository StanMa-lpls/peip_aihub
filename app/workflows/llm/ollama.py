"""Ollama chat client for workflows.

This mirrors the local LLM smoke test in ``tests/test_local_llm.py`` and calls
Ollama's native ``/api/chat`` endpoint directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.settings import OllamaSettings, ollama_settings


def _chat_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/chat"


@dataclass(frozen=True, slots=True)
class OllamaChatMessage:
    """Small response wrapper compatible with the workflow explain node."""

    content: str
    raw_response: dict[str, Any]


class OllamaChatClient:
    """Minimal Ollama /api/chat client with an invoke(prompt) interface."""

    def __init__(self, settings: OllamaSettings) -> None:
        settings.validate()
        self._settings = settings

    def invoke(self, prompt: str) -> OllamaChatMessage:
        raw = chat_once(
            self._settings.base_url,
            self._settings.model,
            [{"role": "user", "content": prompt}],
            timeout_seconds=self._settings.timeout_seconds,
        )
        message = raw.get("message") or {}
        return OllamaChatMessage(
            content=str(message.get("content") or "").strip(),
            raw_response=raw,
        )


def create_ollama_chat_model(settings: OllamaSettings | None = None) -> OllamaChatClient:
    """Create a local Ollama chat client from runtime settings."""

    active_settings = settings or ollama_settings
    return OllamaChatClient(active_settings)


def chat_once(
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Call Ollama /api/chat once with stream disabled."""

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    response = httpx.post(
        _chat_url(base_url),
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def message_content_to_text(message: Any) -> str:
    """Normalize a chat response content into plain text."""

    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content).strip()
