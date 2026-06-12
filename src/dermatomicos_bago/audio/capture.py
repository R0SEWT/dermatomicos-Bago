from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from ..config import DetectConfig


def load_wav_16k(path: str, target_sr: int = 16000) -> np.ndarray:
    data, sr = sf.read(path, dtype="float32", always_2d=False)
    if data.ndim == 2:
        data = data.mean(axis=1)
    if sr != target_sr:
        g = gcd(sr, target_sr)
        data = resample_poly(data, target_sr // g, sr // g).astype(np.float32)
    return np.asarray(data, dtype=np.float32)


def mic_frames(cfg: DetectConfig):
    """Generador infinito de frames float32 de `frame_seconds` desde el micrófono."""
    import sounddevice as sd

    n = int(cfg.frame_seconds * cfg.sample_rate)
    with sd.InputStream(samplerate=cfg.sample_rate, channels=1, dtype="float32") as stream:
        while True:
            block, _ = stream.read(n)
            yield block[:, 0].copy()


def rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(frame)))) if len(frame) else 0.0
