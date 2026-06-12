import sys
import time
import pathlib
from dataclasses import dataclass
from typing import Protocol

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


class _NightLike(Protocol):
    """Estructura mínima que consume la tendencia: la satisfacen _Night y NightFeatures."""
    cry_load: float
    scratch_load: float
    awakenings: int


@dataclass
class _Night:
    """Vista mínima de una noche leída de gold para alimentar el reporte de tendencia."""
    cry_load: float
    scratch_load: float
    awakenings: int


def _load_real_nights(out_root: str = "data/gold", n: int | None = None) -> list[_Night]:
    """Lee las noches persistidas en gold (ordenadas) como vistas para la tendencia."""
    df = read_nights(str(pathlib.Path(out_root) / "nights"))
    if df.is_empty():
        return []
    if n is not None:
        df = df.tail(n)  # últimas n noches (read_nights ya ordena por night_ts)
    return [
        _Night(cry_load=c, scratch_load=s, awakenings=a)
        for c, s, a in zip(df["cry_load"], df["scratch_load"], df["awakenings"])
    ]


def _emit_trend(
    nights: list[_NightLike], out_root: str = "data/gold", synthetic: bool = False
) -> pathlib.Path:
    """Recompone la curva acumulada, escribe el reporte trend e imprime el sparkline."""
    cfg = SeverityConfig()
    loads = [(f.cry_load, f.scratch_load) for f in nights]
    curve = severity_curve(loads, cfg)
    md = build_trend_report(nights, curve, cfg, synthetic=synthetic)
    reports_dir = pathlib.Path(out_root) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"trend_{time.time_ns()}.md"
    out.write_text(md)
    spark = sparkline(curve, lo=0.0, hi=cfg.max_value)
    print(f"Tendencia ({len(curve)} noches): {spark}")
    print(f"Severidad acumulada: {curve[-1] if curve else 0.0:.2f} / {cfg.max_value:.2f}")
    print(f"Reporte tendencia: {out}")
    return out


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
    print(f"\nReporte noche: {out}\nNoche: {night_path}\nSeveridad noche: {tracker.value:.2f}")
    # Si ya hay historial, mostrar también la trayectoria multinoche (incluye esta noche).
    nights = _load_real_nights(out_root)
    if len(nights) >= 2:
        _emit_trend(nights, out_root=out_root)


def run_trend(synthetic: bool = False, n: int = 7):
    if synthetic:
        nights = synthetic_nights(n)
    else:
        nights = _load_real_nights(n=n)
        if not nights:
            print(
                "data/gold/nights/ está vacío. Corre sesiones (derma live/replay) "
                "o usa: derma trend --synthetic"
            )
            return
    _emit_trend(nights, synthetic=synthetic)


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
