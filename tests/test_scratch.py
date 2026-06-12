import numpy as np
import polars as pl

from dermatomicos_bago.models.scratch import ScratchHead


def _toy_df(n=80, seed=0):
    rng = np.random.default_rng(seed)
    pos = rng.normal(1.0, 0.1, (n, 1024))
    neg = rng.normal(-1.0, 0.1, (n, 1024))
    rows = (
        [{"label": "positive", **{f"e{i}": float(v) for i, v in enumerate(r)}} for r in pos]
        + [{"label": "negative", **{f"e{i}": float(v) for i, v in enumerate(r)}} for r in neg]
    )
    return pl.DataFrame(rows)


def test_train_and_predict_separable():
    head = ScratchHead().fit(_toy_df())
    assert head.predict_proba(np.full(1024, 1.0, dtype=np.float32)) > 0.8   # positive
    assert head.predict_proba(np.full(1024, -1.0, dtype=np.float32)) < 0.2  # negative


def test_save_load_roundtrip(tmp_path):
    head = ScratchHead().fit(_toy_df())
    p = tmp_path / "head.joblib"
    head.save(str(p))
    loaded = ScratchHead.load(str(p))
    a = head.predict_proba(np.full(1024, 1.0, dtype=np.float32))
    b = loaded.predict_proba(np.full(1024, 1.0, dtype=np.float32))
    assert abs(a - b) < 1e-9
