import numpy as np
from typing import Sequence

from ..config import DetectConfig


def resolve_class_indices(class_names: Sequence[str], wanted: Sequence[str]) -> list[int]:
    wanted_set = set(wanted)
    return [i for i, name in enumerate(class_names) if name in wanted_set]


def cry_score(scores: np.ndarray, cry_indices: Sequence[int]) -> float:
    if not cry_indices:
        return 0.0
    return float(np.max(scores[list(cry_indices)]))


def classify_frame(cry: float, scratch: float, rms: float, cfg: DetectConfig) -> str:
    if scratch >= cfg.scratch_threshold:
        return "scratch"
    if cry >= cfg.cry_threshold:
        return "cry"
    if rms < cfg.quiet_rms:
        return "quiet"
    return "other"
