import numpy as np

from dermatomicos_bago.audio.windowing import sliding_windows


def test_yields_full_frames_at_each_hop():
    samples = np.arange(10, dtype=np.float32)
    frames = list(sliding_windows(samples, frame_len=4, hop_len=2))
    assert [f.tolist() for f in frames] == [
        [0, 1, 2, 3], [2, 3, 4, 5], [4, 5, 6, 7], [6, 7, 8, 9],
    ]


def test_drops_trailing_partial_frame():
    samples = np.arange(9, dtype=np.float32)
    frames = list(sliding_windows(samples, frame_len=4, hop_len=4))
    assert [f.tolist() for f in frames] == [[0, 1, 2, 3], [4, 5, 6, 7]]
