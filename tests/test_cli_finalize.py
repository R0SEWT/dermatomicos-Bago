from dermatomicos_bago.cli import _finalize
from dermatomicos_bago.pipeline.nights import read_nights, NIGHT_COLUMNS


def test_finalize_emits_trend_after_two_nights(tmp_path):
    out_root = str(tmp_path)
    # primera noche: sin trend todavía (1 sola noche)
    _finalize(["quiet"] * 100 + ["cry"] * 20, out_root=out_root)
    assert not list((tmp_path / "reports").glob("trend_*.md"))
    # segunda noche: ahora sí emite la tendencia multinoche
    _finalize(["quiet"] * 110 + ["scratch"] * 10, out_root=out_root)
    trend = list((tmp_path / "reports").glob("trend_*.md"))
    assert len(trend) == 1
    md = trend[0].read_text()
    assert "(2 noches)" in md          # la curva refleja 2 noches
    assert "\n| 2 |" in md             # tabla con fila para la 2da noche


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
