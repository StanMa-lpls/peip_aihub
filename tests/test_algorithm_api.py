from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes.algorithm_dynamic_route import create_algorithm_api_router
from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.service import get_algorithm_registry
from app.application import create_app


def _fake_registry() -> AlgorithmRegistry:
    return AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.fake": {
                    "package": "fake-apc",
                    "class_path": "tests.fakes.FakeAPCController",
                    "metadata": {
                        "api_path": "apc/fake",
                    },
                }
            }
        }
    )


def test_list_algorithms_route() -> None:
    app = create_app()
    app.dependency_overrides[get_algorithm_registry] = _fake_registry
    client = TestClient(app)

    response = client.get("/api/v1/algorithms")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"][0]["algorithm_id"] == "apc.fake"
    assert body["data"][0]["package"] == "fake-apc"


def test_get_algorithm_instruction_route_returns_metadata() -> None:
    app = create_app()
    app.dependency_overrides[get_algorithm_registry] = _fake_registry
    client = TestClient(app)

    response = client.get("/api/v1/algorithms/instruction/apc.fake")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["algorithm_id"] == "apc.fake"
    assert data["metadata"]["description"] == "Fake APC metadata"
    assert data["metadata"]["when_to_use"] == "用于测试算法 metadata 展示。"
    assert data["metadata"]["input_model"] == "tests.fakes.FakeAPCInput"


def test_dynamic_algorithm_route_uses_configured_io_models() -> None:
    registry = _fake_registry()
    app = create_app()
    app.dependency_overrides[get_algorithm_registry] = lambda: registry
    app.include_router(create_algorithm_api_router(registry), prefix="/api/v1")
    client = TestClient(app)

    response = client.post(
        "/api/v1/algorithms/apc/fake",
        json={"machine_id": "M1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"] == {"adjustments": {"rb": [1.0, 0.0]}}


def test_dynamic_algorithm_route_openapi_uses_clean_summary() -> None:
    registry = _fake_registry()
    app = create_app()
    app.dependency_overrides[get_algorithm_registry] = lambda: registry
    app.include_router(create_algorithm_api_router(registry), prefix="/api/v1")
    client = TestClient(app)

    operation = client.get("/openapi.json").json()["paths"]["/api/v1/algorithms/apc/fake"]["post"]

    assert operation["summary"] == "Apc Fake"
    assert operation["operationId"] == "apc_fake"
    assert "Invoke" not in operation["summary"]


def test_dynamic_algorithm_route_skips_algorithms_without_api_path() -> None:
    registry = AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.internal": {
                    "class_path": "tests.fakes.FakeAPCController",
                }
            }
        }
    )
    app = create_app()
    app.dependency_overrides[get_algorithm_registry] = lambda: registry
    app.include_router(create_algorithm_api_router(registry), prefix="/api/v1")
    client = TestClient(app)

    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/algorithms/apc/internal" not in paths
    assert registry.invoke("apc.internal", {"machine_id": "M1"}) == {"adjustments": {"rb": [1.0, 0.0]}}


