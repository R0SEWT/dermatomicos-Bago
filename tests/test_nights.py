from dermatomicos_bago.pipeline.features import NightFeatures
from dermatomicos_bago.pipeline.nights import (
    NIGHT_COLUMNS,
    night_row,
    write_night,
    read_nights,
)


def _feats(cry_s=600.0, scr_s=300.0):
    return NightFeatures(
        night_seconds=28800.0,
        cry_seconds=cry_s,
        cry_events=5,
        scratch_seconds=scr_s,
        scratch_events=8,
        quiet_seconds=27000.0,
        awakenings=4,
    )


def test_night_row_has_all_columns_and_derived():
    row = night_row(_feats(), severity=0.42, night_ts=1700)
    assert set(row.keys()) == set(NIGHT_COLUMNS)
    assert row["night_ts"] == 1700
    assert row["severity"] == 0.42
    # derivados presentes
    assert abs(row["cry_load"] - 600.0 / 28800.0) < 1e-9


def test_write_read_roundtrip(tmp_path):
    out = str(tmp_path / "nights")
    write_night(_feats(cry_s=600), severity=0.30, night_ts=200, out_dir=out)
    write_night(_feats(cry_s=900), severity=0.55, night_ts=100, out_dir=out)
    df = read_nights(out)
    assert df.columns == NIGHT_COLUMNS
    assert df.height == 2
    # ordenado por night_ts ascendente
    assert list(df["night_ts"]) == [100, 200]
    assert df["cry_seconds"][0] == 900.0


def test_read_empty_returns_schema(tmp_path):
    df = read_nights(str(tmp_path / "nope"))
    assert df.is_empty()
    assert df.columns == NIGHT_COLUMNS
