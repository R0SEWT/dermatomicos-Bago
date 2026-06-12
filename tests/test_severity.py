from dermatomicos_bago.pipeline.severity import SeverityTracker
from dermatomicos_bago.config import SeverityConfig


def test_bad_nights_raise_and_clamp():
    t = SeverityTracker(SeverityConfig())
    for _ in range(10):
        t.update(cry_load=1.0, scratch_load=1.0)
    assert t.value == SeverityConfig().max_value   # clamped a 1.0


def test_clean_nights_decay_toward_zero():
    t = SeverityTracker(SeverityConfig())
    t.update(cry_load=1.0, scratch_load=1.0)
    peak = t.value
    for _ in range(20):
        t.update(cry_load=0.0, scratch_load=0.0)
    assert t.value < peak and t.value < 0.05


def test_history_tracks_each_update():
    t = SeverityTracker(SeverityConfig())
    t.update(0.5, 0.5)
    t.update(0.0, 0.0)
    assert len(t.history) == 2
