"""Typed configuration objects for wheel-backed algorithms."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.algorithms.exceptions import AlgorithmConfigError


@dataclass(frozen=True, slots=True)
class ConstructorSpec:
    """How to instantiate a configured algorithm class."""

    mode: str = "none"
    args: tuple[Any, ...] = ()
    kwargs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CallSpec:
    """How to call an instantiated algorithm object."""

    mode: str
    method: str | None = None
    steps: tuple[str, ...] = ()
    input_factory: str | None = None


@dataclass(frozen=True, slots=True)
class AlgorithmSpec:
    """A normalized algorithm config entry."""

    algorithm_id: str
    family: str
    class_path: str
    package: str | None = None
    constructor: ConstructorSpec = field(default_factory=ConstructorSpec)
    call: CallSpec = field(default_factory=lambda: CallSpec(mode="auto"))
    cache: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, algorithm_id: str, data: Mapping[str, Any]) -> "AlgorithmSpec":
        aid = _required_text(algorithm_id, "algorithm_id")
        class_path = _required_text(data.get("class_path"), f"{aid}.class_path")
        family = _optional_text(data.get("family")) or _family_from_algorithm_id(aid)
        constructor = _parse_constructor(data.get("constructor"))
        call = _parse_call(data.get("call"), aid)
        package = data.get("package")
        if package is not None and not isinstance(package, str):
            raise AlgorithmConfigError(f"{aid}.package must be a string")
        cache = data.get("cache", True)
        if not isinstance(cache, bool):
            raise AlgorithmConfigError(f"{aid}.cache must be a boolean")
        metadata = data.get("metadata") or {}
        if not isinstance(metadata, Mapping):
            raise AlgorithmConfigError(f"{aid}.metadata must be an object")
        return cls(
            algorithm_id=aid,
            family=family,
            class_path=class_path,
            package=package,
            constructor=constructor,
            call=call,
            cache=cache,
            metadata=dict(metadata),
        )


def parse_algorithm_specs(config: Mapping[str, Any]) -> dict[str, AlgorithmSpec]:
    """Parse the top-level config mapping into algorithm specs."""

    algorithms = config.get("algorithms")
    if not isinstance(algorithms, Mapping) or not algorithms:
        raise AlgorithmConfigError("config must contain a non-empty 'algorithms' object")
    specs: dict[str, AlgorithmSpec] = {}
    for algorithm_id, raw_spec in algorithms.items():
        if not isinstance(raw_spec, Mapping):
            raise AlgorithmConfigError(f"{algorithm_id!r} spec must be an object")
        spec = AlgorithmSpec.from_mapping(str(algorithm_id), raw_spec)
        specs[spec.algorithm_id] = spec
    return specs


def _parse_constructor(raw: Any) -> ConstructorSpec:
    if raw is None:
        return ConstructorSpec()
    if not isinstance(raw, Mapping):
        raise AlgorithmConfigError("constructor must be an object")
    mode = str(raw.get("mode", "none")).strip().lower()
    if mode not in {"none", "kwargs", "positional", "config"}:
        raise AlgorithmConfigError("constructor.mode must be one of: none, kwargs, positional, config")
    args = raw.get("args", ())
    kwargs = raw.get("kwargs", {})
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    if not isinstance(args, list | tuple):
        raise AlgorithmConfigError("constructor.args must be a list")
    if not isinstance(kwargs, Mapping):
        raise AlgorithmConfigError("constructor.kwargs must be an object")
    return ConstructorSpec(mode=mode, args=tuple(args), kwargs=dict(kwargs))


def _parse_call(raw: Any, algorithm_id: str) -> CallSpec:
    if raw is None:
        return CallSpec(mode="auto")
    if not isinstance(raw, Mapping):
        raise AlgorithmConfigError(f"{algorithm_id}.call must be an object")
    mode = _required_text(raw.get("mode"), f"{algorithm_id}.call.mode").lower()
    input_factory = raw.get("input_factory")
    if input_factory is not None:
        input_factory = _required_text(input_factory, f"{algorithm_id}.call.input_factory")
    if mode == "method":
        method = _required_text(raw.get("method"), f"{algorithm_id}.call.method")
        return CallSpec(mode=mode, method=method, input_factory=input_factory)
    if mode == "pipeline":
        steps = raw.get("steps")
        if not isinstance(steps, list | tuple) or not steps:
            raise AlgorithmConfigError(f"{algorithm_id}.call.steps must be a non-empty list")
        normalized_steps = tuple(_required_text(step, f"{algorithm_id}.call.steps[]") for step in steps)
        return CallSpec(mode=mode, steps=normalized_steps, input_factory=input_factory)
    if mode == "auto":
        return CallSpec(mode=mode, input_factory=input_factory)
    raise AlgorithmConfigError(f"{algorithm_id}.call.mode must be one of: method, pipeline, auto")


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AlgorithmConfigError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _family_from_algorithm_id(algorithm_id: str) -> str:
    return algorithm_id.split(".", 1)[0]
