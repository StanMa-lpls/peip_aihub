"""Exceptions for algorithm loading and dispatch."""

from __future__ import annotations


class AlgorithmConfigError(ValueError):
    """Raised when an algorithm config cannot be parsed."""


class AlgorithmLoadError(RuntimeError):
    """Raised when an algorithm class or instance cannot be loaded."""


class AlgorithmNotFoundError(KeyError):
    """Raised when an algorithm_id is not registered."""


class AlgorithmInvocationError(RuntimeError):
    """Raised when a registered algorithm cannot be invoked."""
