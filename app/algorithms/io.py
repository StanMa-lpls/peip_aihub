"""Input/output model conversion for configured algorithms."""

from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from typing import Any

from app.algorithms.exceptions import AlgorithmInvocationError
from app.algorithms.importing import import_object
from app.algorithms.specs import AlgorithmSpec


def parse_input(spec: AlgorithmSpec, payload: Any) -> Any:
    """Convert raw API payload into the configured input model."""

    model_path = _metadata_text(spec, "input_model")
    if not model_path:
        return payload
    model = import_object(model_path)
    try:
        return _parse_with_model(model, payload)
    except Exception as exc:
        raise AlgorithmInvocationError(
            f"{spec.algorithm_id} input payload does not match {model_path}: {exc}"
        ) from exc


def normalize_output(spec: AlgorithmSpec, result: Any) -> Any:
    """Normalize an algorithm result through the configured output model."""

    model_path = _metadata_text(spec, "output_model")
    if not model_path:
        return result
    model = import_object(model_path)
    if isinstance(result, model):
        return result
    try:
        return _parse_with_model(model, result)
    except Exception as exc:
        raise AlgorithmInvocationError(
            f"{spec.algorithm_id} output does not match {model_path}: {exc}"
        ) from exc


def describe_io_models(spec: AlgorithmSpec) -> dict[str, Any]:
    """Return configured input/output model paths and available schemas."""

    return {
        "algorithm_id": spec.algorithm_id,
        "input": describe_model(_metadata_text(spec, "input_model")),
        "output": describe_model(_metadata_text(spec, "output_model")),
    }


def describe_model(model_path: str) -> dict[str, Any] | None:
    """Describe one configured model without requiring a request payload."""

    if not model_path:
        return None
    model = import_object(model_path)
    schema = _json_schema(model)
    fields_info = _fields(model)
    return {
        "class_path": model_path,
        "schema": schema,
        "fields": fields_info,
    }


def _parse_with_model(model: Any, value: Any) -> Any:
    if isinstance(value, model):
        return value
    if hasattr(model, "model_validate") and callable(model.model_validate):
        return model.model_validate(value)
    if hasattr(model, "parse_obj") and callable(model.parse_obj):
        return model.parse_obj(value)
    if hasattr(model, "from_dict") and callable(model.from_dict):
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return value if isinstance(value, model) else model.from_dict(value.to_dict())
        return model.from_dict(value)
    if is_dataclass(model) and isinstance(value, dict):
        return model(**value)
    if isinstance(value, dict):
        return model(**value)
    return value if isinstance(value, model) else model(value)


def _metadata_text(spec: AlgorithmSpec, key: str) -> str:
    value = spec.metadata.get(key)
    return value.strip() if isinstance(value, str) else ""


def _json_schema(model: Any) -> dict[str, Any] | None:
    if hasattr(model, "model_json_schema") and callable(model.model_json_schema):
        return model.model_json_schema()
    if hasattr(model, "schema") and callable(model.schema):
        return model.schema()
    return None


def _fields(model: Any) -> list[dict[str, Any]]:
    if is_dataclass(model):
        return [
            {
                "name": field.name,
                "type": _type_name(field.type),
                "required": field.default is MISSING and field.default_factory is MISSING,
            }
            for field in fields(model)
        ]
    annotations = getattr(model, "__annotations__", {})
    if isinstance(annotations, dict):
        return [
            {
                "name": name,
                "type": _type_name(annotation),
                "required": True,
            }
            for name, annotation in annotations.items()
        ]
    return []


def _type_name(value: Any) -> str:
    return getattr(value, "__name__", str(value))
