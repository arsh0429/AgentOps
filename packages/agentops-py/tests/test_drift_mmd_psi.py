import numpy as np
from agentops.drift.mmd import MMDDetector
from agentops.drift.psi import PSIDetector


def test_mmd_does_not_fire_on_same_distribution() -> None:
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, size=(50, 8))
    mmd = MMDDetector(reference=ref, threshold=0.05, window=50)
    fired = False
    for _ in range(50):
        v = rng.normal(0, 1, size=8)
        if mmd.update(v):
            fired = True
    assert not fired

def test_mmd_fires_on_distribution_shift() -> None:
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1, size=(50, 8))
    mmd = MMDDetector(reference=ref, threshold=0.05, window=50)
    fired = False
    for _ in range(80):
        v = rng.normal(2, 1, size=8)
        if mmd.update(v):
            fired = True
            break
    assert fired

def test_psi_zero_on_identical_distributions() -> None:
    psi = PSIDetector(reference={"a": 50, "b": 30, "c": 20}, threshold=0.1)
    for _ in range(50):
        psi.update("a")
    for _ in range(30):
        psi.update("b")
    for _ in range(20):
        psi.update("c")
    assert not psi.is_drifted()
    assert psi.value() < 0.05

def test_psi_fires_when_distribution_shifts() -> None:
    psi = PSIDetector(reference={"a": 50, "b": 30, "c": 20}, threshold=0.2)
    for _ in range(10):
        psi.update("a")
    for _ in range(10):
        psi.update("b")
    for _ in range(80):
        psi.update("c")
    assert psi.is_drifted()
