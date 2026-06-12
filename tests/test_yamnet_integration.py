import numpy as np
import pytest


@pytest.mark.slow
def test_yamnet_loads_and_infers_silence():
    from dermatomicos_bago.models.yamnet import YamnetModel
    from dermatomicos_bago.models.labels import resolve_class_indices, cry_score

    m = YamnetModel()
    assert len(m.class_names) == 521
    scores, emb = m.infer(np.zeros(16000, dtype=np.float32))
    assert scores.shape == (521,) and emb.shape == (1024,)
    # silencio no debe disparar llanto
    cry_idx = resolve_class_indices(m.class_names, ("Baby cry, infant cry", "Crying, sobbing"))
    assert cry_score(scores, cry_idx) < 0.1
