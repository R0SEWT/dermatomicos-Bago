import pathlib

import joblib
import numpy as np
import polars as pl
from sklearn.neural_network import MLPClassifier

from .yamnet import YamnetModel
from ..audio.capture import load_wav_16k
from ..audio.windowing import sliding_windows

_EMB_COLS = [f"e{i}" for i in range(1024)]


def embed_clips(root: str, yamnet: YamnetModel, sample_rate: int = 16000) -> pl.DataFrame:
    """Recorre data/bronze/scratch/<label>/*.wav -> embeddings por ventana de 1s + label."""
    rows = []
    for wav in pathlib.Path(root).glob("*/*.wav"):
        label = wav.parent.name
        audio = load_wav_16k(str(wav))
        for frame in sliding_windows(audio, sample_rate, sample_rate):  # 1s, sin solape
            _, emb = yamnet.infer(frame)
            rows.append({"label": label, **{f"e{i}": float(v) for i, v in enumerate(emb)}})
    return pl.DataFrame(rows)


class ScratchHead:
    def __init__(self, positive_label: str = "positive"):
        self.positive_label = positive_label
        self.clf = MLPClassifier(hidden_layer_sizes=(256, 128), max_iter=400, random_state=0)

    def fit(self, df: pl.DataFrame) -> "ScratchHead":
        X = df.select(_EMB_COLS).to_numpy()
        y = (df.get_column("label") == self.positive_label).to_numpy().astype(int)
        self.clf.fit(X, y)
        return self

    def predict_proba(self, embedding: np.ndarray) -> float:
        x = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        return float(self.clf.predict_proba(x)[0, 1])

    def save(self, path: str):
        joblib.dump((self.positive_label, self.clf), path)

    @classmethod
    def load(cls, path: str) -> "ScratchHead":
        label, clf = joblib.load(path)
        h = cls(label)
        h.clf = clf
        return h
