from dermatomicos_bago.pipeline.events import Event
from dermatomicos_bago.pipeline.features import aggregate
from dermatomicos_bago.config import FeatureConfig


def test_aggregate_basic_counts():
    events = [
        Event(0, 60, "quiet"), Event(60, 90, "cry"), Event(90, 150, "quiet"),
        Event(150, 165, "scratch"), Event(165, 600, "quiet"),
    ]
    f = aggregate(events, night_seconds=600, cfg=FeatureConfig(min_quiet_seconds=30))
    assert f.cry_seconds == 30 and f.cry_events == 1
    assert f.scratch_seconds == 15 and f.scratch_events == 1
    # despertares: tramo quiet>=30 seguido de evento activo -> 2
    assert f.awakenings == 2


def test_loads_are_normalized_0_1():
    f = aggregate([Event(0, 100, "cry")], night_seconds=100, cfg=FeatureConfig())
    assert 0.0 <= f.cry_load <= 1.0 and f.cry_load == 1.0
