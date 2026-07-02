"""Top-level API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.algorithm_dynamic_route import create_algorithm_api_router
from app.api.routes.algorithm_route import algorithm_router
from app.api.routes.workflow_route import workflow_router
from app.core.settings import settings

route = APIRouter(prefix=settings.API_V1_STR)

route.include_router(algorithm_router)
route.include_router(workflow_router)
route.include_router(create_algorithm_api_router())
