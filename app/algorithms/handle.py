"""Uniform invocation wrapper for configured algorithms."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.algorithms.exceptions import AlgorithmInvocationError
from app.algorithms.importing import import_object
from app.algorithms.io import normalize_output, parse_input
from app.algorithms.specs import AlgorithmSpec, CallSpec


@dataclass(slots=True)
class AlgorithmHandle:
    """A loaded algorithm instance plus its invocation metadata."""

    spec: AlgorithmSpec
    instance: Any

    @property
    def algorithm_id(self) -> str:
        return self.spec.algorithm_id

    @property
    def family(self) -> str:
        return self.spec.family

    def invoke(self, payload: Any) -> Any:
        """Invoke the wrapped algorithm and return JSON-friendly data."""

        parsed_input = parse_input(self.spec, payload)
        call_spec = self.spec.call
        if self.spec.metadata.get("input_model") and call_spec.input_factory:
            call_spec = replace(call_spec, input_factory=None)
        result = CallAdapter(call_spec).invoke(self.instance, parsed_input)
        normalized_output = normalize_output(self.spec, result)
        return to_jsonable(normalized_output)


class CallAdapter:
    """Apply a configured call strategy to an algorithm instance."""

    def __init__(self, spec: CallSpec) -> None:
        self._spec = spec

    def invoke(self, instance: Any, payload: Any) -> Any:
        current = self._prepare_input(payload)
        if self._spec.mode == "auto":
            return _call_auto(instance, current)
        if self._spec.mode == "method":
            if self._spec.method is None:
                raise AlgorithmInvocationError("method call requires call.method")
            return _call_method(instance, self._spec.method, current)
        if self._spec.mode == "pipeline":
            for step in self._spec.steps:
                current = _call_method(instance, step, current)
            return current
        raise AlgorithmInvocationError(f"unsupported call mode: {self._spec.mode}")

    def _prepare_input(self, payload: Any) -> Any:
        if not self._spec.input_factory:
            return payload
        factory = import_object(self._spec.input_factory)
        if not callable(factory):
            raise AlgorithmInvocationError(f"input_factory {self._spec.input_factory!r} is not callable")
        return factory(payload)


def _call_method(instance: Any, method_name: str, argument: Any) -> Any:
    method = getattr(instance, method_name, None)
    if not callable(method):
        raise AlgorithmInvocationError(
            f"{type(instance).__name__} does not provide callable method {method_name!r}"
        )
    return method(argument)


def _call_auto(instance: Any, payload: Any) -> Any:
    invoke = getattr(instance, "invoke", None)
    if callable(invoke):
        return invoke(payload)

    adjust = getattr(instance, "adjust", None)
    if callable(adjust):
        result = adjust(payload)
        to_response = getattr(instance, "to_response", None)
        if callable(to_response):
            return to_response(result)
        return result

    raise AlgorithmInvocationError(
        f"{type(instance).__name__} does not provide invoke() or adjust() for auto call"
    )


def to_jsonable(value: Any) -> Any:
    """Convert common wheel return objects into JSON-friendly structures."""

    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_jsonable(value.to_dict())
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return value
