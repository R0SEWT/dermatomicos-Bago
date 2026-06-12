"""Graba clips de N segundos a data/bronze/scratch/<label>/. Uso:
   uv run python scripts/record_dataset.py positive 15
   uv run python scripts/record_dataset.py negative 15
"""
import sys
import time
import pathlib

import numpy as np  # noqa: F401  (sounddevice devuelve ndarray)
import soundfile as sf
import sounddevice as sd


def main():
    label, secs = sys.argv[1], float(sys.argv[2])
    out = pathlib.Path("data/bronze/scratch") / label
    out.mkdir(parents=True, exist_ok=True)
    print(f"Grabando {secs}s de '{label}'... rasca/haz ruido cerca del mic")
    x = sd.rec(int(secs * 16000), samplerate=16000, channels=1, dtype="float32")
    sd.wait()
    fn = out / f"{int(time.time())}.wav"
    sf.write(fn, x[:, 0], 16000)
    print("guardado", fn)


if __name__ == "__main__":
    main()
