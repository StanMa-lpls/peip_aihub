"""Dynamic algorithm routes with OpenAPI input/output models."""

from __future__ import annotations

from inspect import Parameter, Signature
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field, create_model

from app.algorithms.exceptions import (
    AlgorithmConfigError,
    AlgorithmInvocationError,
    AlgorithmLoadError,
    AlgorithmNotFoundError,
)
from app.algorithms.importing import import_object
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.service import get_algorithm_registry
from app.common import response


def create_algorithm_api_router(registry: AlgorithmRegistry | None = None) -> APIRouter:
    """Create per-algorithm routes for algorithms with configured IO models."""

    registry = registry or get_algorithm_registry()
    router = APIRouter(prefix="/algorithms", tags=["Algorithm APIs"])
    for algorithm_id in registry.algorithm_ids:
        spec = registry.get_spec(algorithm_id)
        if spec is None:
            continue
        route_path = _configured_route_path(spec.metadata)
        if not route_path:
            continue
        input_model_path = _metadata_text(spec.metadata, "input_model")
        output_model_path = (
            _metadata_text(spec.metadata, "output_model")
            or _metadata_text(spec.metadata, "result_model")
        )
        if not input_model_path:
            continue
        try:
            input_model = import_object(input_model_path)
            output_model = import_object(output_model_path) if output_model_path else Any
        except AlgorithmLoadError:
            # The wheel may not be installed in every environment. Keep generic
            # APIs available and register the typed route once the wheel exists.
            continue

        api_path = "/" + route_path
        response_model = _response_model(_model_name(algorithm_id), output_model)
        endpoint = _endpoint(algorithm_id, input_model)
        endpoint.__name__ = _operation_id(route_path)
        endpoint.__annotations__["return"] = response_model
        router.add_api_route(
            api_path,
            endpoint,
            methods=["POST"],
            summary=_route_summary(spec.metadata, route_path),
            operation_id=_operation_id(route_path),
            response_model=response_model,
        )
    return router


def _endpoint(algorithm_id: str, input_model: Any):
    example = _model_example(input_model)
    body = Body(..., examples=[example] if example is not None else None)

    async def invoke_typed_algorithm(
        payload: Any = body,
        registry: AlgorithmRegistry = Depends(get_algorithm_registry),
    ) -> BaseModel:
        try:
            result = registry.invoke(algorithm_id, payload)
        except AlgorithmNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (AlgorithmConfigError, AlgorithmLoadError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except AlgorithmInvocationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - wheel-specific errors vary
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
        return await response.success(data=result)

    invoke_typed_algorithm.__signature__ = Signature(  # type: ignore[attr-defined]
        parameters=[
            Parameter(
                "payload",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=body,
                annotation=input_model,
            ),
            Parameter(
                "registry",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=Depends(get_algorithm_registry),
                annotation=AlgorithmRegistry,
            ),
        ],
        return_annotation=BaseModel,
    )
    return invoke_typed_algorithm


def _response_model(name: str, output_model: Any) -> type[BaseModel]:
    return create_model(
        f"{name}Response",
        code=(int, Field(default=0, description="业务状态码，0 表示成功")),
        message=(str, Field(default="success", description="响应消息")),
        data=(output_model, Field(default=None, description="算法输出")),
    )


def _configured_route_path(metadata: dict[str, Any]) -> str:
    configured = _metadata_text(metadata, "api_path") or _metadata_text(metadata, "route_path")
    return configured.strip("/") if configured else ""


def _route_summary(metadata: dict[str, Any], route_path: str) -> str:
    configured = _metadata_text(metadata, "summary") or _metadata_text(metadata, "title")
    if configured:
        return configured
    return " ".join(part.replace("-", " ").replace("_", " ").title() for part in route_path.split("/"))


def _operation_id(route_path: str) -> str:
    return "_".join(part.replace("-", "_").replace(".", "_") for part in route_path.split("/") if part)


def _model_name(algorithm_id: str) -> str:
    return "".join(part.title().replace("_", "") for part in algorithm_id.split("."))


def _model_example(model: Any) -> Any:
    if hasattr(model, "model_json_schema") and callable(model.model_json_schema):
        schema = model.model_json_schema()
        return schema.get("example") or (schema.get("examples") or [None])[0]
    if hasattr(model, "schema") and callable(model.schema):
        schema = model.schema()
        return schema.get("example") or (schema.get("examples") or [None])[0]
    return None


def _metadata_text(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    return value.strip() if isinstance(value, str) else ""
