import numpy as np
import soundfile as sf

from dermatomicos_bago.audio.capture import load_wav_16k


def test_load_wav_resamples_to_16k(tmp_path):
    p = tmp_path / "tone.wav"
    sr = 48000
    x = np.sin(2 * np.pi * 440 * np.arange(sr) / sr).astype(np.float32)  # 1s @ 48k
    sf.write(p, x, sr)
    y = load_wav_16k(str(p))
    assert y.dtype == np.float32
    assert abs(len(y) - 16000) <= 1   # ~1s a 16k
