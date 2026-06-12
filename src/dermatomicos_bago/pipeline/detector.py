from typing import Callable, Optional, TYPE_CHECKING

from ..config import DetectConfig
from ..models.yamnet import YamnetModel
from ..models.labels import resolve_class_indices, cry_score, classify_frame
from ..audio.capture import mic_frames, rms, load_wav_16k
from ..audio.windowing import sliding_windows
from .events import Event
from .smoothing import LabelSmoother

if TYPE_CHECKING:
    from ..models.scratch import ScratchHead


class StreamDetector:
    def __init__(self, cfg: DetectConfig | None = None,
                 yamnet: "YamnetModel | None" = None,
                 scratch: Optional["ScratchHead"] = None,
                 smoother: LabelSmoother | None = None):
        self.cfg = cfg or DetectConfig()
        self.yamnet = yamnet or YamnetModel()
        self.scratch = scratch
        self.smoother = smoother or LabelSmoother(self.cfg.smooth_min_run)
        self.cry_idx = resolve_class_indices(self.yamnet.class_names, self.cfg.cry_class_names)

    def classify(self, frame) -> Event:
        scores, emb = self.yamnet.infer(frame)
        cry = cry_score(scores, self.cry_idx)
        scr = self.scratch.predict_proba(emb) if self.scratch else 0.0
        label = classify_frame(cry=cry, scratch=scr, rms=rms(frame), cfg=self.cfg)
        conf = {"cry": cry, "scratch": scr}.get(label, 1.0)
        return Event(0.0, self.cfg.frame_seconds, label, conf)

    def _emit(self, frame, t: float, on_event: Callable[[Event], None]) -> float:
        raw = self.classify(frame)
        label = self.smoother.push(raw.label)
        on_event(Event(t, t + self.cfg.frame_seconds, label, raw.score))
        return t + self.cfg.frame_seconds

    def run_live(self, on_event: Callable[[Event], None]):
        """Bloquea: captura del mic y emite Events suavizados (~1/seg). API para la UI."""
        t = 0.0
        for frame in mic_frames(self.cfg):
            t = self._emit(frame, t, on_event)

    def run_file(self, path: str, on_event: Callable[[Event], None]):
        """Replay: corre el pipeline sobre un WAV grabado. Mismo stream de Events que run_live."""
        audio = load_wav_16k(path, self.cfg.sample_rate)
        frame_len = int(self.cfg.frame_seconds * self.cfg.sample_rate)
        hop_len = int(self.cfg.hop_seconds * self.cfg.sample_rate)
        t = 0.0
        for frame in sliding_windows(audio, frame_len, hop_len):
            t = self._emit(frame, t, on_event)
