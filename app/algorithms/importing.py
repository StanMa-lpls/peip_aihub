"""Import helpers for dotted Python object paths used by algorithms."""

from __future__ import annotations

import importlib
from typing import Any

from app.algorithms.exceptions import AlgorithmLoadError


def import_object(dotted_path: str) -> Any:
    """Import an object from a dotted path."""

    path = dotted_path.strip()
    if not path or "." not in path:
        raise AlgorithmLoadError(f"invalid dotted path: {dotted_path!r}")

    parts = path.split(".")
    last_error: Exception | None = None
    for idx in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:idx])
        attr_parts = parts[idx:]
        try:
            obj = importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - exact import errors vary
            last_error = exc
            continue
        try:
            for attr in attr_parts:
                obj = getattr(obj, attr)
            return obj
        except AttributeError as exc:
            last_error = exc
            break

    detail = f": {last_error}" if last_error is not None else ""
    raise AlgorithmLoadError(f"cannot import object {dotted_path!r}{detail}")
