from typing import Callable, Optional, TYPE_CHECKING

from ..config import DetectConfig
from ..models.yamnet import YamnetModel
from ..models.labels import resolve_class_indices, cry_score, classify_frame
from ..audio.capture import mic_frames, rms
from .events import Event

if TYPE_CHECKING:
    from ..models.scratch import ScratchHead


class StreamDetector:
    def __init__(self, cfg: DetectConfig | None = None,
                 yamnet: YamnetModel | None = None,
                 scratch: Optional["ScratchHead"] = None):
        self.cfg = cfg or DetectConfig()
        self.yamnet = yamnet or YamnetModel()
        self.scratch = scratch
        self.cry_idx = resolve_class_indices(self.yamnet.class_names, self.cfg.cry_class_names)

    def classify(self, frame) -> Event:
        scores, emb = self.yamnet.infer(frame)
        cry = cry_score(scores, self.cry_idx)
        scr = self.scratch.predict_proba(emb) if self.scratch else 0.0
        label = classify_frame(cry=cry, scratch=scr, rms=rms(frame), cfg=self.cfg)
        conf = {"cry": cry, "scratch": scr}.get(label, 1.0)
        return Event(0.0, self.cfg.frame_seconds, label, conf)

    def run_live(self, on_event: Callable[[Event], None]):
        """Bloquea: captura del mic y emite un Event (~1/seg) por on_event. API para la UI."""
        t = 0.0
        for frame in mic_frames(self.cfg):
            ev = self.classify(frame)
            ev = Event(t, t + self.cfg.frame_seconds, ev.label, ev.score)
            on_event(ev)
            t += self.cfg.frame_seconds
