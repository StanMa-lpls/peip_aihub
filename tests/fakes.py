from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class FakeCfg:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = dict(payload or {})


@dataclass
class FakeEvent:
    name: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "score": self.score}


class FakeOEEAnalyzer:
    def __init__(self, cfg: FakeCfg) -> None:
        self.cfg = cfg

    def process_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"sensor": payload["sensor"], "threshold": self.cfg.payload["params"]["threshold"]}

    def detect(self, data: dict[str, Any]) -> list[FakeEvent]:
        return [FakeEvent(name=data["sensor"], score=float(data["threshold"]))]


@dataclass
class FakeAPCInput:
    machine_id: str
    process: str = "RB"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FakeAPCInput":
        return cls(
            machine_id=str(payload["machine_id"]),
            process=str(payload.get("process", "RB")).upper(),
        )


@dataclass
class FakeAPCResult:
    adjustments: dict[str, list[float]]

    def to_dict(self) -> dict[str, Any]:
        return {"adjustments": self.adjustments}


class FakeAPCController:
    @staticmethod
    def get_algorithm_metadata(config: dict[str, Any] | None = None) -> dict[str, Any]:
        config = dict(config or {})
        return {
            "algorithm_id": config.get("algorithm_id", "apc.fake"),
            "family": "apc",
            "description": "Fake APC metadata",
            "when_to_use": "用于测试算法 metadata 展示。",
            "capabilities": ["adjust"],
            "input_model": "tests.fakes.FakeAPCInput",
            "output_model": "tests.fakes.FakeAPCResult",
            "tags": ["apc", "fake"],
        }

    def adjust(self, payload: FakeAPCInput) -> FakeAPCResult:
        return FakeAPCResult(adjustments={payload.process.lower(): [1.0, 0.0]})


class FakeTypedAPCController:
    def adjust(self, payload: FakeAPCInput) -> dict[str, Any]:
        return {"adjustments": {payload.machine_id.lower(): [3.0]}}


class FakeFactoryAlgorithm:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = self.config["metadata"]
        return {
            "algorithm_id": metadata["algorithm_id"],
            "family": metadata["family"],
            "strict_process": self.config.get("strict_process", False),
            "payload": payload,
        }


def create_fake_algorithm(config: dict[str, Any]) -> FakeFactoryAlgorithm:
    return FakeFactoryAlgorithm(config)


class FakeAdjustAlgorithm:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def adjust(self, payload: dict[str, Any]) -> FakeAPCResult:
        process = str(payload.get("process", "RB")).lower()
        return FakeAPCResult(adjustments={process: [float(payload["value"])]})

    def to_response(self, result: FakeAPCResult) -> dict[str, Any]:
        response = result.to_dict()
        response["algorithm_id"] = self.config["metadata"]["algorithm_id"]
        return response


def create_fake_adjust_algorithm(config: dict[str, Any]) -> FakeAdjustAlgorithm:
    return FakeAdjustAlgorithm(config)
