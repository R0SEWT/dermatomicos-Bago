import sys
import time
import pathlib

from .config import DetectConfig, FeatureConfig, SeverityConfig
from .models.scratch import ScratchHead
from .pipeline.detector import StreamDetector
from .pipeline.events import frames_to_episodes
from .pipeline.features import aggregate
from .pipeline.severity import SeverityTracker
from .pipeline.report import ReportBuilder


def run_live(duration_s: float = 60.0):
    head_path = pathlib.Path("models/scratch_head.joblib")
    scratch = ScratchHead.load(str(head_path)) if head_path.exists() else None
    det = StreamDetector(scratch=scratch)
    labels: list[str] = []
    print(f"Escuchando {duration_s}s...  Ctrl-C para terminar antes")
    t0 = time.time()

    def on_event(ev):
        labels.append(ev.label)
        print(f"[{ev.t_start:5.0f}s] {ev.label:8s} {ev.score:.2f}")
        if time.time() - t0 > duration_s:
            raise KeyboardInterrupt

    try:
        det.run_live(on_event)
    except KeyboardInterrupt:
        pass
    _finalize(labels)


def _finalize(labels: list[str]):
    frame_s = DetectConfig().frame_seconds
    episodes = frames_to_episodes(labels, frame_s)
    night_s = len(labels) * frame_s
    feats = aggregate(episodes, night_s, FeatureConfig())
    tracker = SeverityTracker(SeverityConfig())
    tracker.update(feats.cry_load, feats.scratch_load)
    pathlib.Path("data/gold/reports").mkdir(parents=True, exist_ok=True)
    out = pathlib.Path("data/gold/reports") / f"{int(time.time())}.md"
    out.write_text(ReportBuilder().build(feats, tracker))
    print(f"\nReporte: {out}\nSeveridad: {tracker.value:.2f}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "live"
    if cmd == "live":
        run_live(float(sys.argv[2]) if len(sys.argv) > 2 else 60.0)
    else:
        print("uso: derma live [segundos]")
        sys.exit(1)


if __name__ == "__main__":
    main()
