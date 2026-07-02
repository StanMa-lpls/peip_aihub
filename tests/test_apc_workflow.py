from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.service import get_algorithm_registry
from app.application import create_app
from app.workflows.nodes.apc import make_apc_algorithm_node
from app.workflows.runner import run_apc_adjust_workflow


class FakeLLM:
    def __init__(self, content: str = "APC 调整结果解释") -> None:
        self.content = content
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> object:
        self.prompts.append(prompt)
        return type("FakeMessage", (), {"content": self.content})()


def _fake_registry() -> AlgorithmRegistry:
    return AlgorithmRegistry.from_mapping(
        {
            "algorithms": {
                "apc.r2r_controller": {
                    "family": "apc",
                    "class_path": "tests.fakes.FakeAPCController",
                }
            }
        }
    )


def _apc_payload(process: str = "RB") -> dict[str, Any]:
    return {
        "machine_id": "M1",
        "tube_id": "T1",
        "target_p": 100.0,
        "p_data": {"p1_mean": [96.0, 97.0, 98.0]},
        "adj_data": {},
        "adjust_max_limit": 2,
        "process": process,
    }


def test_apc_algorithm_node_invokes_adjust_capability() -> None:
    node = make_apc_algorithm_node(registry=_fake_registry())

    update = node({"apc_input": _apc_payload("LP"), "trace": []})

    assert update["apc_result"] == {"adjustments": {"lp": [1.0, 0.0]}}
    assert update["trace"][0]["node"] == "apc_algorithm"
    assert update["trace"][0]["result"] == "success"


def test_run_apc_adjust_workflow_runs_algorithm_then_explanation() -> None:
    llm = FakeLLM("建议按 APC 输出执行调整。")

    result = run_apc_adjust_workflow(
        _apc_payload("RB"),
        registry=_fake_registry(),
        llm=llm,
    )

    assert result["apc_result"] == {"adjustments": {"rb": [1.0, 0.0]}}
    assert result["explanation"] == "建议按 APC 输出执行调整。"
    assert "APC 算法输出" in llm.prompts[0]
    assert [item["node"] for item in result["trace"]] == ["apc_algorithm", "llm_explain"]


def test_apc_adjust_workflow_api_returns_common_response(monkeypatch) -> None:
    def fake_runner(
        apc_input: dict[str, Any],
        *,
        registry: AlgorithmRegistry | None = None,
        llm: Any | None = None,
        ollama_config: Any | None = None,
    ) -> dict[str, Any]:
        return {
            "explanation": f"已解释 {apc_input['machine_id']}",
            "explanation_error": None,
            "apc_result": {"adjustments": {"rb": [1.0, 0.0]}},
            "trace": [{"node": "apc_algorithm", "result": "success"}],
            "elapsed_seconds": 0.01,
        }

    import app.api.routes.workflow_route as workflow_route

    monkeypatch.setattr(workflow_route, "run_apc_adjust_workflow", fake_runner)

    app = create_app()
    app.dependency_overrides[get_algorithm_registry] = _fake_registry
    client = TestClient(app)

    response = client.post("/api/v1/workflows/apc/adjust", json=_apc_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["explanation"] == "已解释 M1"
    assert body["data"]["apc_result"] == {"adjustments": {"rb": [1.0, 0.0]}}


def test_apc_adjust_workflow_api_returns_422_for_invalid_apc_input() -> None:
    app = create_app()
    app.dependency_overrides[get_algorithm_registry] = _fake_registry
    client = TestClient(app)

    payload = _apc_payload()
    payload.pop("tube_id")
    payload.pop("target_p")

    response = client.post("/api/v1/workflows/apc/adjust", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "data"}
    assert body["code"] == 422
    assert body["message"] == "Workflow input validation failed"
    assert body["data"]["error"] == (
        "ValueError: invalid APC input: machine_id, tube_id and positive target_p are required"
    )
