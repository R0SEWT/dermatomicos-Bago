import numpy as np
from typing import Iterator


def sliding_windows(samples: np.ndarray, frame_len: int, hop_len: int) -> Iterator[np.ndarray]:
    """Yield views of length `frame_len` every `hop_len`; drop trailing partial frame."""
    n = len(samples)
    start = 0
    while start + frame_len <= n:
        yield samples[start:start + frame_len]
        start += hop_len
