import random

from agentops.drift.adwin import ADWIN


def test_adwin_does_not_fire_on_stationary_stream() -> None:
    random.seed(0)
    a = ADWIN(delta=0.002)
    fired = False
    for _ in range(2000):
        if a.update(random.gauss(0.7, 0.05)):
            fired = True
            break
    assert not fired, "ADWIN should not fire on stationary stream"

def test_adwin_fires_on_mean_shift() -> None:
    random.seed(1)
    a = ADWIN(delta=0.002)
    fired_at = None
    for i in range(2000):
        v = random.gauss(0.8, 0.05) if i < 800 else random.gauss(0.4, 0.05)
        if a.update(v) and fired_at is None:
            fired_at = i
    assert fired_at is not None
    assert 800 < fired_at < 1300, f"fired at {fired_at}"
