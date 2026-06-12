from dataclasses import dataclass

from .events import Event
from ..config import FeatureConfig


@dataclass(frozen=True)
class NightFeatures:
    night_seconds: float
    cry_seconds: float
    cry_events: int
    scratch_seconds: float
    scratch_events: int
    quiet_seconds: float
    awakenings: int

    @property
    def cry_load(self) -> float:
        return self.cry_seconds / self.night_seconds if self.night_seconds else 0.0

    @property
    def scratch_load(self) -> float:
        return self.scratch_seconds / self.night_seconds if self.night_seconds else 0.0

    @property
    def sleep_fragmentation(self) -> float:
        return self.awakenings / (self.night_seconds / 3600) if self.night_seconds else 0.0


def _dur(e: Event) -> float:
    return e.t_end - e.t_start


def aggregate(events: list[Event], night_seconds: float, cfg: FeatureConfig) -> NightFeatures:
    cry_s = sum(_dur(e) for e in events if e.label == "cry")
    scr_s = sum(_dur(e) for e in events if e.label == "scratch")
    quiet_s = sum(_dur(e) for e in events if e.label == "quiet")
    cry_n = sum(1 for e in events if e.label == "cry")
    scr_n = sum(1 for e in events if e.label == "scratch")
    awakenings = 0
    for prev, cur in zip(events, events[1:]):
        if (prev.label == "quiet" and _dur(prev) >= cfg.min_quiet_seconds
                and cur.label in cfg.awakening_active_label):
            awakenings += 1
    return NightFeatures(night_seconds, cry_s, cry_n, scr_s, scr_n, quiet_s, awakenings)
