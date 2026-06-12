from dermatomicos_bago.pipeline.smoothing import LabelSmoother


def test_first_frame_commits_immediately():
    s = LabelSmoother(min_run=2)
    assert s.push("quiet") == "quiet"


def test_single_frame_spike_is_suppressed():
    s = LabelSmoother(min_run=2)
    out = [s.push(x) for x in ["quiet", "quiet", "cry", "quiet", "quiet"]]
    assert out == ["quiet", "quiet", "quiet", "quiet", "quiet"]


def test_sustained_change_commits_after_min_run():
    s = LabelSmoother(min_run=2)
    out = [s.push(x) for x in ["quiet", "cry", "cry", "cry"]]
    # 1er cry: candidato (count 1) -> aún quiet; 2do cry: count 2 -> commit cry
    assert out == ["quiet", "quiet", "cry", "cry"]


def test_min_run_1_is_passthrough():
    s = LabelSmoother(min_run=1)
    seq = ["quiet", "cry", "other", "quiet"]
    assert [s.push(x) for x in seq] == seq


def test_competing_candidates_reset_the_counter():
    s = LabelSmoother(min_run=2)
    # cry, scratch alternados nunca acumulan min_run del mismo -> se mantiene quiet
    out = [s.push(x) for x in ["quiet", "cry", "scratch", "cry", "scratch"]]
    assert out == ["quiet", "quiet", "quiet", "quiet", "quiet"]
