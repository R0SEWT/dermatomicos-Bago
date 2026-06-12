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
    assert labels.count("cry") >= 1 and labels[-1] == "cry"
