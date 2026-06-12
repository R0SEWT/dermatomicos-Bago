import sys
import time
import pathlib
from dataclasses import dataclass

from .config import DetectConfig, FeatureConfig, SeverityConfig
from .models.scratch import ScratchHead
from .pipeline.detector import StreamDetector
from .pipeline.events import frames_to_episodes
from .pipeline.features import aggregate
from .pipeline.severity import SeverityTracker
from .pipeline.report import ReportBuilder
from .pipeline.nights import write_night, read_nights
from .pipeline.trend import severity_curve, sparkline, synthetic_nights, build_trend_report


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


def run_file_cmd(path: str):
    head_path = pathlib.Path("models/scratch_head.joblib")
    scratch = ScratchHead.load(str(head_path)) if head_path.exists() else None
    det = StreamDetector(scratch=scratch)
    labels: list[str] = []
    print(f"Replay de {path} ...")

    def on_event(ev):
        labels.append(ev.label)
        print(f"[{ev.t_start:5.0f}s] {ev.label:8s} {ev.score:.2f}")

    det.run_file(path, on_event)
    _finalize(labels)


def _finalize(labels: list[str], out_root: str = "data/gold"):
    frame_s = DetectConfig().frame_seconds
    episodes = frames_to_episodes(labels, frame_s)
    night_s = len(labels) * frame_s
    feats = aggregate(episodes, night_s, FeatureConfig())
    tracker = SeverityTracker(SeverityConfig())
    tracker.update(feats.cry_load, feats.scratch_load)
    night_ts = time.time_ns()  # ns para que sesiones en el mismo segundo no colisionen
    reports_dir = pathlib.Path(out_root) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"{night_ts}.md"
    out.write_text(ReportBuilder().build(feats, tracker))
    night_path = write_night(feats, tracker.value, night_ts, str(pathlib.Path(out_root) / "nights"))
    print(f"\nReporte: {out}\nNoche: {night_path}\nSeveridad: {tracker.value:.2f}")


def run_trend(synthetic: bool = False, n: int = 7):
    cfg = SeverityConfig()
    if synthetic:
        nights = synthetic_nights(n)
    else:
        df = read_nights()
        if df.is_empty():
            print(
                "data/gold/nights/ está vacío. Corre sesiones (derma live/replay) "
                "o usa: derma trend --synthetic"
            )
            return
        df = df.tail(n)  # últimas n noches (read_nights ya ordena por night_ts)
        nights = [
            _Night(cry_load=c, scratch_load=s, awakenings=a)
            for c, s, a in zip(df["cry_load"], df["scratch_load"], df["awakenings"])
        ]
    loads = [(f.cry_load, f.scratch_load) for f in nights]
    curve = severity_curve(loads, cfg)
    md = build_trend_report(nights, curve, cfg, synthetic=synthetic)
    reports_dir = pathlib.Path("data/gold/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"trend_{int(time.time())}.md"
    out.write_text(md)
    spark = sparkline(curve, lo=0.0, hi=cfg.max_value)
    print(f"Curva ({len(curve)} noches): {spark}")
    print(f"Severidad actual: {curve[-1] if curve else 0.0:.2f} / {cfg.max_value:.2f}")
    print(f"Reporte: {out}")


@dataclass
class _Night:
    """Vista mínima de una noche leída de gold para alimentar el reporte de tendencia."""
    cry_load: float
    scratch_load: float
    awakenings: int


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "live"
    if cmd == "live":
        run_live(float(sys.argv[2]) if len(sys.argv) > 2 else 60.0)
    elif cmd == "replay":
        if len(sys.argv) < 3:
            print("uso: derma replay <archivo.wav>")
            sys.exit(1)
        run_file_cmd(sys.argv[2])
    elif cmd == "trend":
        args = sys.argv[2:]
        synthetic = "--synthetic" in args
        n = next((int(a) for a in args if a.isdigit()), 7)
        run_trend(synthetic=synthetic, n=n)
    else:
        print("uso: derma [live [segundos] | replay <archivo.wav> | trend [--synthetic] [n]]")
        sys.exit(1)


if __name__ == "__main__":
    main()
