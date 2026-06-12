import numpy as np

from dermatomicos_bago.models.labels import resolve_class_indices, cry_score, classify_frame
from dermatomicos_bago.config import DetectConfig

CLASS_NAMES = ["Speech", "Crying, sobbing", "Baby cry, infant cry", "Silence", "Music"]


def test_resolve_class_indices_by_name():
    idx = resolve_class_indices(CLASS_NAMES, ("Baby cry, infant cry", "Crying, sobbing"))
    assert sorted(idx) == [1, 2]


def test_cry_score_is_max_over_cry_classes():
    scores = np.array([0.1, 0.3, 0.7, 0.0, 0.0])
    assert cry_score(scores, [1, 2]) == 0.7


def test_classify_frame_precedence_scratch_over_cry():
    cfg = DetectConfig()
    assert classify_frame(cry=0.9, scratch=0.8, rms=0.5, cfg=cfg) == "scratch"


def test_classify_frame_cry_when_above_threshold():
    cfg = DetectConfig()
    assert classify_frame(cry=0.5, scratch=0.1, rms=0.5, cfg=cfg) == "cry"


def test_classify_frame_quiet_when_low_rms():
    cfg = DetectConfig()
    assert classify_frame(cry=0.0, scratch=0.0, rms=0.001, cfg=cfg) == "quiet"


def test_classify_frame_other_otherwise():
    cfg = DetectConfig()
    assert classify_frame(cry=0.0, scratch=0.0, rms=0.5, cfg=cfg) == "other"
