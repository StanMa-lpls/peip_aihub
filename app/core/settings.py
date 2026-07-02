"""Application settings loaded from configs/.env."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.algorithms.exceptions import AlgorithmConfigError


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env_file(path: str | Path | None = None) -> dict[str, str]:
    """Load simple KEY=value pairs from a .env file without extra dependencies."""

    env_path = Path(path) if path is not None else project_root() / "configs" / ".env"
    if not env_path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if key:
            values[key] = value
            os.environ.setdefault(key, value)
    return values


def load_config_file(path: str | Path) -> dict[str, Any]:
    """Load a JSON/YAML config file into a mapping."""

    config_path = Path(path)
    suffix = config_path.suffix.lower()
    text = config_path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise AlgorithmConfigError("YAML config requires PyYAML to be installed") from exc
        data = yaml.safe_load(text)
    else:
        raise AlgorithmConfigError(f"unsupported config file extension: {config_path.suffix}")
    if not isinstance(data, dict):
        raise AlgorithmConfigError("config file must contain an object at top level")
    return data


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings used by API and service layers."""

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PEIP AI Hub"
    PROJECT_VERSION: str = "0.1.0"
    PROJECT_DESCRIPTION: str = "PEIP algorithm capability gateway"
    ENVIRONMENT: str = "development"
    ALGORITHM_CONFIG_FILE: str = ""

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Settings":
        values = load_env_file(env_file)
        root = project_root()
        default_config = root / "configs" / "algorithms.yaml"

        def _get(*names: str, default: str) -> str:
            for name in names:
                value = os.environ.get(name) or values.get(name)
                if value:
                    return value
            return default

        def _config_path(value: str) -> str:
            path = Path(value)
            if path.is_absolute():
                return str(path)
            return str(root / "configs" / path)

        return cls(
            API_V1_STR=_get("API", "PEIP_AIHUB_API_V1_STR", default="/api/v1").rstrip("/"),
            PROJECT_NAME=_get("NAME", "PEIP_AIHUB_PROJECT_NAME", default="PEIP AI Hub"),
            PROJECT_VERSION=_get("VERSION", "PEIP_AIHUB_PROJECT_VERSION", default="0.1.0"),
            PROJECT_DESCRIPTION=_get(
                "DESCRIPTION",
                "PEIP_AIHUB_PROJECT_DESCRIPTION",
                default="PEIP algorithm capability gateway",
            ),
            ENVIRONMENT=_get("ENV", "PEIP_AIHUB_ENV", default="development"),
            ALGORITHM_CONFIG_FILE=_config_path(
                _get("ALGORITHMS_FILE", "PEIP_AIHUB_ALGORITHM_CONFIG", default=str(default_config))
            ),
        )


@dataclass(frozen=True, slots=True)
class LLMSettings:
    """LLM runtime settings."""

    endpoint: str
    api_key: str
    model_opus: str
    model_sonnet: str
    model_fast: str

    @property
    def base_url(self) -> str:
        """Return OpenAI SDK compatible base_url."""

        endpoint = self.endpoint.rstrip("/")
        for suffix in ("/chat/completions", "/chat/completion"):
            if endpoint.endswith(suffix):
                return endpoint[: -len(suffix)]
        return endpoint

    @property
    def models(self) -> dict[str, str]:
        return {
            "opus": self.model_opus,
            "sonnet": self.model_sonnet,
            "fast": self.model_fast,
        }

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "LLMSettings":
        values = load_env_file(env_file)

        def _get(name: str) -> str:
            return os.environ.get(name) or values.get(name, "")

        return cls(
            endpoint=_get("LLM_ENDPOINT"),
            api_key=_get("LLM_API_KEY"),
            model_opus=_get("LLM_MODEL_OPUS"),
            model_sonnet=_get("LLM_MODEL_SONNET"),
            model_fast=_get("LLM_MODEL_FAST"),
        )

    def validate(self) -> None:
        missing = [
            name
            for name, value in {
                "LLM_ENDPOINT": self.endpoint,
                "LLM_API_KEY": self.api_key,
                "LLM_MODEL_OPUS": self.model_opus,
                "LLM_MODEL_SONNET": self.model_sonnet,
                "LLM_MODEL_FAST": self.model_fast,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing LLM settings: {', '.join(missing)}")


@dataclass(frozen=True, slots=True)
class OllamaSettings:
    """Local Ollama runtime settings."""

    base_url: str = ""
    model: str = ""
    timeout_seconds: float = 120.0

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "OllamaSettings":
        values = load_env_file(env_file)

        def _get(name: str, default: str) -> str:
            return os.environ.get(name) or values.get(name, default)

        timeout_raw = _get("OLLAMA_TIMEOUT_SECONDS", "120")
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError:
            timeout_seconds = 120.0

        return cls(
            base_url=_get("OLLAMA_BASE_URL", cls.base_url).rstrip("/"),
            model=_get("OLLAMA_MODEL", cls.model),
            timeout_seconds=timeout_seconds,
        )

    def validate(self) -> None:
        missing = [
            name
            for name, value in {
                "OLLAMA_BASE_URL": self.base_url,
                "OLLAMA_MODEL": self.model,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing Ollama settings: {', '.join(missing)}")


settings = Settings.from_env()
llm_settings = LLMSettings.from_env()
ollama_settings = OllamaSettings.from_env()
