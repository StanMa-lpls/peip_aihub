"""Instantiate wheel-backed algorithms from normalized specs."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.algorithms.exceptions import AlgorithmConfigError, AlgorithmLoadError
from app.algorithms.importing import import_object
from app.algorithms.specs import AlgorithmSpec

_REFERENCE_RE = re.compile(r"^\$\{(?P<kind>resource|env):(?P<value>[^}]+)\}$")


class ValueResolver:
    """Resolve constructor values from config into Python objects."""

    def resolve(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._resolve_string(value)
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, dict):
            if "factory" in value:
                return self._build_factory_value(value)
            return {key: self.resolve(item) for key, item in value.items()}
        return value

    def _resolve_string(self, value: str) -> Any:
        match = _REFERENCE_RE.match(value.strip())
        if match is None:
            return value
        kind = match.group("kind")
        ref = match.group("value").strip()
        if kind == "env":
            return os.environ.get(ref, "")
        if kind == "resource":
            obj = import_object(ref)
            return str(obj) if isinstance(obj, Path) else obj
        raise AlgorithmConfigError(f"unsupported reference kind: {kind}")

    def _build_factory_value(self, value: dict[str, Any]) -> Any:
        factory_path = value.get("factory")
        if not isinstance(factory_path, str) or not factory_path.strip():
            raise AlgorithmConfigError("factory value must contain a non-empty 'factory' path")
        factory = import_object(factory_path)
        if not callable(factory):
            raise AlgorithmLoadError(f"factory {factory_path!r} is not callable")
        payload = self.resolve(value.get("value"))
        if isinstance(payload, dict) and value.get("mode") == "kwargs":
            return factory(**payload)
        return factory(payload)


class AlgorithmLoader:
    """Build algorithm instances from `AlgorithmSpec`."""

    def __init__(self, resolver: ValueResolver | None = None) -> None:
        self._resolver = resolver or ValueResolver()

    def load(self, spec: AlgorithmSpec) -> Any:
        cls = import_object(spec.class_path)
        if not callable(cls):
            raise AlgorithmLoadError(f"{spec.class_path!r} is not callable")

        constructor = spec.constructor
        if constructor.mode == "none":
            if _is_algorithm_factory(spec.class_path):
                return cls(self._build_algorithm_config(spec))
            return cls()
        if constructor.mode == "kwargs":
            kwargs = {key: self._resolver.resolve(value) for key, value in constructor.kwargs.items()}
            return cls(**kwargs)
        if constructor.mode == "positional":
            args = [self._resolver.resolve(value) for value in constructor.args]
            return cls(*args)
        if constructor.mode == "config":
            config = self._build_algorithm_config(spec)
            return cls(config)
        raise AlgorithmConfigError(f"unsupported constructor mode: {constructor.mode}")

    def _build_algorithm_config(self, spec: AlgorithmSpec) -> dict[str, Any]:
        """Build a single factory config from peip-owned metadata and constructor kwargs."""
        kwargs = {key: self._resolver.resolve(value) for key, value in spec.constructor.kwargs.items()}
        metadata = dict(spec.metadata)
        metadata.setdefault("algorithm_id", spec.algorithm_id)
        metadata.setdefault("family", spec.family)
        config: dict[str, Any] = {"metadata": metadata}
        config.update(kwargs)
        return config


def _is_algorithm_factory(class_path: str) -> bool:
    _, _, name = class_path.rpartition(".")
    return name == "create_algorithm" or name.startswith("create_")
