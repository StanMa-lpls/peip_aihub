"""Smoke test for the APC_Test wheel-style package."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

from apc_engine import create_algorithm  # noqa: E402


def main() -> int:
    # This inline mapping represents the peip-owned configuration that would be
    # passed to the wheel factory after package discovery.
    algorithm = create_algorithm(
        {
            "metadata": {
                "algorithm_id": "apc.test.r2r_controller",
                "version": "0.1.0",
                "description": "APC_Test 统一 Run-to-Run APC 控制器",
                "tags": ["test", "pseudo", "r2r"],
            },
        }
    )
    payload = {
        "algorithm_id": "apc.test.r2r_controller",
        "machine_id": "M01",
        "tube_id": "T01",
        "target_p": 100.0,
        "p_data": {"p1_mean": [96.0, 97.0, 98.0], "Time": ["t1", "t2", "t3"]},
        "adj_data": {},
        "adjust_max_limit": 2,
        "process": "RB",
    }

    result = algorithm.adjust(payload)
    print(
        json.dumps(
            {
                "metadata": algorithm.metadata.to_dict(),
                "response": algorithm.to_response(result),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
