from __future__ import annotations

import math
from collections import deque


class ADWIN:
    """Adaptive Windowing (Bifet & Gavaldà, 2007). One-dimensional change
    detector over a stream of bounded values. Maintains a window of recent
    values and removes older sub-windows when their mean differs from the
    newer sub-window by more than a Hoeffding-derived bound.

    Linear-buffer implementation for clarity; the original paper uses
    compressed buckets. For portfolio-scale streams (≤10^4) this is adequate.
    """
    name = "adwin"

    def __init__(self, delta: float = 0.002, max_window: int = 5000) -> None:
        self.delta = float(delta)
        self.max_window = int(max_window)
        self._window: deque[float] = deque()
        self._drifted = False
        self._last_value = 0.0
        self._last_threshold = 0.0

    def _bound(self, n0: int, n1: int) -> float:
        m = 1.0 / (1.0 / n0 + 1.0 / n1)
        return math.sqrt((1.0 / (2.0 * m)) * math.log(4.0 * (n0 + n1) / self.delta))

    def update(self, value: float) -> bool:
        v = float(value)
        self._last_value = v
        self._window.append(v)
        if len(self._window) > self.max_window:
            self._window.popleft()

        n = len(self._window)
        if n < 10:
            self._drifted = False
            return False
        arr = list(self._window)
        cumsum = [0.0]
        for x in arr:
            cumsum.append(cumsum[-1] + x)

        for split in range(5, n - 5):
            n0, n1 = split, n - split
            mean0 = cumsum[split] / n0
            mean1 = (cumsum[n] - cumsum[split]) / n1
            eps = self._bound(n0, n1)
            self._last_threshold = eps
            if abs(mean0 - mean1) > eps:
                drop = split if mean0 < mean1 else 0
                if drop > 0:
                    for _ in range(drop):
                        self._window.popleft()
                self._drifted = True
                return True
        self._drifted = False
        return False

    def is_drifted(self) -> bool:
        return self._drifted

    def value(self) -> float:
        return self._last_value

    def threshold(self) -> float:
        return self._last_threshold

    def reset(self) -> None:
        self._window.clear()
        self._drifted = False
        self._last_value = 0.0
        self._last_threshold = 0.0
