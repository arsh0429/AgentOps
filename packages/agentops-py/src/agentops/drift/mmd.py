from __future__ import annotations

from collections import deque

import numpy as np
from numpy.typing import NDArray


class MMDDetector:
    """Maximum Mean Discrepancy with an RBF kernel.

    Estimates MMD^2 between a fixed reference set and a sliding window of
    recent samples. Fires when MMD^2 exceeds `threshold`. Bandwidth via the
    median heuristic at construction time.
    """
    name = "mmd_rbf"

    def __init__(self, reference: NDArray[np.floating], *, threshold: float = 0.05,
                 window: int = 50, gamma: float | None = None) -> None:
        self.reference = np.asarray(reference, dtype=np.float64)
        self.threshold_value = float(threshold)
        self.window = int(window)
        self._buf: deque[NDArray[np.float64]] = deque(maxlen=window)
        self._drifted = False
        self._last_value = 0.0
        if gamma is None:
            gamma = self._median_heuristic(self.reference)
        self.gamma = float(gamma)

    @staticmethod
    def _median_heuristic(x: NDArray[np.float64]) -> float:
        if len(x) < 2:
            return 1.0
        n = min(len(x), 200)
        sub = x[:n]
        d = sub[:, None, :] - sub[None, :, :]
        sq = (d * d).sum(axis=-1)
        med = float(np.median(sq[sq > 0])) if (sq > 0).any() else 1.0
        return 1.0 / max(med, 1e-9)

    def _kernel_mean(self, a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
        d = a[:, None, :] - b[None, :, :]
        sq = (d * d).sum(axis=-1)
        k = np.exp(-self.gamma * sq)
        return float(k.mean())

    def update(self, value: NDArray[np.floating]) -> bool:
        v = np.asarray(value, dtype=np.float64).reshape(-1)
        self._buf.append(v)
        if len(self._buf) < self.window:
            self._drifted = False
            return False
        cur = np.stack(list(self._buf), axis=0)
        mmd2 = (self._kernel_mean(self.reference, self.reference)
                + self._kernel_mean(cur, cur)
                - 2.0 * self._kernel_mean(self.reference, cur))
        self._last_value = float(max(0.0, mmd2))
        self._drifted = self._last_value > self.threshold_value
        return self._drifted

    def is_drifted(self) -> bool:
        return self._drifted

    def value(self) -> float:
        return self._last_value

    def threshold(self) -> float:
        return self.threshold_value

    def reset(self) -> None:
        self._buf.clear()
        self._drifted = False
        self._last_value = 0.0
