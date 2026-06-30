"""Smoke test for the OEE_Test aggregate sensor-analysis package."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

from oee_engine import create_algorithm, get_supported_algorithms  # noqa: E402


def main() -> int:
    results = {}
    for algorithm_id in get_supported_algorithms():
        # This inline mapping mirrors the peip-owned config loaded from
        # configs/algorithms.yaml. No api_path/call is needed for workflow use.
        algorithm = create_algorithm(
            {
                "metadata": {
                    "algorithm_id": algorithm_id,
                    "version": "0.1.0",
                },
            }
        )
        payload = {
            "alarm_index": "demo_alarm",
            "alarm_reason": f"{algorithm_id} smoke test",
            "conventional_solution": "check related sensor signal",
            "sensor_name": algorithm_id.rsplit(".", 1)[-1],
            "coordinate": "demo-coordinate",
            "timestamps": ["2026-05-14 20:03:51", "2026-05-14 20:03:52"],
            "values": [1.0, 20.0],
        }

        processed = algorithm.process_data(payload)
        detected = algorithm.detect(processed)
        results[algorithm_id] = {
            "metadata": algorithm.metadata.to_dict(),
            "processed": processed,
            "detected": detected,
        }
    print(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
