import csv

import numpy as np
import tensorflow_hub as hub

YAMNET_HANDLE = "https://tfhub.dev/google/yamnet/1"


class YamnetModel:
    def __init__(self, handle: str = YAMNET_HANDLE):
        self._model = hub.load(handle)
        path = self._model.class_map_path().numpy().decode("utf-8")
        with open(path) as f:
            self.class_names = [row["display_name"] for row in csv.DictReader(f)]

    def infer(self, waveform: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """waveform: float32 mono 16k en [-1,1]. Devuelve (mean_scores[521], mean_embedding[1024])."""
        wav = np.asarray(waveform, dtype=np.float32)
        scores, embeddings, _ = self._model(wav)
        return scores.numpy().mean(axis=0), embeddings.numpy().mean(axis=0)
