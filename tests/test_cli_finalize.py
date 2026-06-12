from dermatomicos_bago.cli import _finalize
from dermatomicos_bago.pipeline.nights import read_nights, NIGHT_COLUMNS


def test_finalize_writes_night_parquet(tmp_path):
    # _finalize es model-free: recibe labels (1 etiqueta/seg), no toca mic ni YAMNet
    labels = ["quiet"] * 60 + ["cry"] * 30 + ["quiet"] * 30
    _finalize(labels, out_root=str(tmp_path))

    df = read_nights(str(tmp_path / "nights"))
    assert df.columns == NIGHT_COLUMNS
    assert df.height == 1
    row = df.row(0, named=True)
    assert row["cry_seconds"] == 30.0
    assert row["night_seconds"] == 120.0
    assert row["severity"] > 0.0
    # también escribió el reporte de una noche
    assert list((tmp_path / "reports").glob("*.md"))
