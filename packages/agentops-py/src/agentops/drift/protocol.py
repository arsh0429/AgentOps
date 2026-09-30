from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DriftDetector(Protocol):
    """One-dimensional online drift detector.

    Implementations consume floats one at a time via `update`. `update` returns
    True when drift has just been detected (edge-triggered). `is_drifted`
    returns the latched state until the next reset.
    """
    name: str

    def update(self, value: float) -> bool: ...
    def is_drifted(self) -> bool: ...
    def value(self) -> float: ...
    def threshold(self) -> float: ...
    def reset(self) -> None: ...
