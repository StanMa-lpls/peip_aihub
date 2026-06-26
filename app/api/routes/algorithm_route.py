"""Algorithm API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.models.algorithm_model import (
    ResponseModel,
)
from app.common import response
from app.algorithms.exceptions import (
    AlgorithmNotFoundError,
)
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.service import (
    get_algorithm_metadata,
    get_algorithm_registry,
    list_algorithms,
)

algorithm_router = APIRouter(prefix="/algorithms", tags=["Algorithms"])


@algorithm_router.get("", summary="List registered algorithms", response_model=ResponseModel)
async def list_algorithm_api(
    registry: AlgorithmRegistry = Depends(get_algorithm_registry),
) -> ResponseModel:
    items = list_algorithms(registry)
    return await response.success(data=items)


@algorithm_router.get("/instruction/{algorithm_id}", summary="Get algorithm metadata", response_model=ResponseModel)
async def get_algorithm_metadata_api(
    algorithm_id: str,
    registry: AlgorithmRegistry = Depends(get_algorithm_registry),
) -> ResponseModel:
    try:
        data = get_algorithm_metadata(registry, algorithm_id)
    except AlgorithmNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await response.success(data=data)
