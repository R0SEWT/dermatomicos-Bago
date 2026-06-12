import numpy as np
import soundfile as sf

from dermatomicos_bago.pipeline.detector import StreamDetector
from dermatomicos_bago.config import DetectConfig


class FakeYamnet:
    """Sustituye a YamnetModel: cry alto si el frame tiene energía, si no silencio."""
    class_names = ["Silence", "Baby cry, infant cry", "Crying, sobbing"]

    def infer(self, frame):
        scores = np.zeros(3, dtype=np.float32)
        emb = np.zeros(1024, dtype=np.float32)
        if float(np.sqrt(np.mean(frame ** 2))) > 0.1:
            scores[1] = 0.9   # "Baby cry, infant cry"
        else:
            scores[0] = 0.9   # "Silence"
        return scores, emb


def _write_wav(path, segments, sr=16000):
    """segments: lista de (amplitud, segundos)."""
    parts = [np.full(int(sec * sr), amp, dtype=np.float32) for amp, sec in segments]
    sf.write(path, np.concatenate(parts), sr)


def test_run_file_emits_quiet_for_silence(tmp_path):
    wav = tmp_path / "silence.wav"
    _write_wav(wav, [(0.0, 5)])   # 5s de silencio
    det = StreamDetector(cfg=DetectConfig(), yamnet=FakeYamnet())
    labels = []
    det.run_file(str(wav), lambda ev: labels.append(ev.label))
    assert labels == ["quiet"] * 5


def test_run_file_smooths_single_frame_spike(tmp_path):
    wav = tmp_path / "blip.wav"
    # quiet,quiet, 1s fuerte (spike), quiet,quiet  -> el smoother (min_run=2) lo suprime
    _write_wav(wav, [(0.0, 2), (0.5, 1), (0.0, 2)])
    det = StreamDetector(cfg=DetectConfig(smooth_min_run=2), yamnet=FakeYamnet())
    labels = []
    det.run_file(str(wav), lambda ev: labels.append(ev.label))
    assert "cry" not in labels and labels == ["quiet"] * 5


def test_run_file_commits_sustained_cry(tmp_path):
    wav = tmp_path / "cry.wav"
    _write_wav(wav, [(0.0, 2), (0.5, 3)])   # 2s quiet + 3s "cry" sostenido
    det = StreamDetector(cfg=DetectConfig(smooth_min_run=2), yamnet=FakeYamnet())
    labels = []
    det.run_file(str(wav), lambda ev: labels.append(ev.label))
    # min_run=2: el 1er frame fuerte aún es quiet; commit cry desde el 2do
    assert labels == ["quiet", "quiet", "quiet", "cry", "cry"]


def test_run_file_resets_smoother_between_streams(tmp_path):
    cry = tmp_path / "cry.wav"
    _write_wav(cry, [(0.5, 3)])    # 3s fuerte -> termina en cry
    sil = tmp_path / "sil.wav"
    _write_wav(sil, [(0.0, 3)])    # 3s silencio
    det = StreamDetector(cfg=DetectConfig(smooth_min_run=2), yamnet=FakeYamnet())
    first = []
    det.run_file(str(cry), lambda ev: first.append(ev.label))
    assert first[-1] == "cry"
    # reusar el detector (sin recargar YAMNet) no debe arrastrar el cry al siguiente WAV
    second = []
    det.run_file(str(sil), lambda ev: second.append(ev.label))
    assert second == ["quiet", "quiet", "quiet"]


def test_run_file_timestamps_use_hop_when_smaller_than_frame(tmp_path):
    wav = tmp_path / "overlap.wav"
    _write_wav(wav, [(0.0, 3)])   # 3s -> ventanas de 1s cada 0.5s = 5 ventanas solapadas
    cfg = DetectConfig(frame_seconds=1.0, hop_seconds=0.5)
    det = StreamDetector(cfg=cfg, yamnet=FakeYamnet())
    events = []
    det.run_file(str(wav), lambda ev: events.append(ev))
    # t_start avanza por el hop, no por la longitud de ventana
    assert [round(e.t_start, 3) for e in events] == [0.0, 0.5, 1.0, 1.5, 2.0]
    # cada ventana dura frame_seconds aunque se solapen (t_end = t_start + frame, no + hop)
    assert all(round(e.t_end - e.t_start, 3) == 1.0 for e in events)


def test_run_file_drops_trailing_partial_window(tmp_path):
    wav = tmp_path / "partial.wav"
    _write_wav(wav, [(0.0, 2.5)])   # 2.5s -> 2 ventanas de 1s, se descarta el 0.5s final
    det = StreamDetector(cfg=DetectConfig(), yamnet=FakeYamnet())
    labels = []
    det.run_file(str(wav), lambda ev: labels.append(ev.label))
    assert labels == ["quiet", "quiet"]
