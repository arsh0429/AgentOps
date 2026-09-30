from __future__ import annotations

import math
from collections import Counter, deque


class PSIDetector:
    """Population Stability Index over a sliding window of categorical values.

    PSI = sum_i (p_cur_i - p_ref_i) * ln(p_cur_i / p_ref_i)
    Above ~0.1 traditionally signals minor shift; ~0.25 major.
    """
    name = "psi"

    def __init__(self, reference: dict[str, float], *, threshold: float = 0.2,
                 window: int = 100, smoothing: float = 1e-4) -> None:
        total = sum(reference.values())
        if total <= 0:
            raise ValueError("reference distribution must be non-empty")
        self._ref = {k: max(v / total, smoothing) for k, v in reference.items()}
        self.threshold_value = float(threshold)
        self.window_size = int(window)
        self.smoothing = smoothing
        self._buf: deque[str] = deque(maxlen=window)
        self._drifted = False
        self._last_value = 0.0

    def update(self, value: str) -> bool:
        self._buf.append(str(value))
        if len(self._buf) < max(20, self.window_size // 2):
            self._drifted = False
            return False
        counts = Counter(self._buf)
        total = sum(counts.values()) or 1
        psi = 0.0
        for k, ref_p in self._ref.items():
            cur_p = max(counts.get(k, 0) / total, self.smoothing)
            psi += (cur_p - ref_p) * math.log(cur_p / ref_p)
        for k, c in counts.items():
            if k in self._ref:
                continue
            cur_p = max(c / total, self.smoothing)
            ref_p = self.smoothing
            psi += (cur_p - ref_p) * math.log(cur_p / ref_p)
        self._last_value = float(psi)
        self._drifted = self._last_value >= self.threshold_value
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
