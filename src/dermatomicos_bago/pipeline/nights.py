"""Persistencia de la capa gold: una fila por noche en data/gold/nights/*.parquet.

Única superficie de disco para las noches. El esquema guarda los campos crudos de
`NightFeatures` + los derivados + la severidad standalone de esa sesión + el epoch.

NOTA sobre `severity`: es la severidad de un tracker fresco actualizado una sola vez
en esa sesión (informativa/auditoría). La curva multi-noche NO la usa — se recompone
replayando un solo acumulador sobre los loads en orden (ver `trend.severity_curve`).
"""

import pathlib

import polars as pl

from .features import NightFeatures

NIGHT_COLUMNS = [
    "night_ts",
    "night_seconds",
    "cry_seconds",
    "cry_events",
    "scratch_seconds",
    "scratch_events",
    "quiet_seconds",
    "awakenings",
    "cry_load",
    "scratch_load",
    "sleep_fragmentation",
    "severity",
]

_SCHEMA = {
    "night_ts": pl.Int64,
    "night_seconds": pl.Float64,
    "cry_seconds": pl.Float64,
    "cry_events": pl.Int64,
    "scratch_seconds": pl.Float64,
    "scratch_events": pl.Int64,
    "quiet_seconds": pl.Float64,
    "awakenings": pl.Int64,
    "cry_load": pl.Float64,
    "scratch_load": pl.Float64,
    "sleep_fragmentation": pl.Float64,
    "severity": pl.Float64,
}


def night_row(f: NightFeatures, severity: float, night_ts: int) -> dict:
    """Arma el dict de una noche (incluye las properties derivadas). Puro."""
    return {
        "night_ts": int(night_ts),
        "night_seconds": float(f.night_seconds),
        "cry_seconds": float(f.cry_seconds),
        "cry_events": int(f.cry_events),
        "scratch_seconds": float(f.scratch_seconds),
        "scratch_events": int(f.scratch_events),
        "quiet_seconds": float(f.quiet_seconds),
        "awakenings": int(f.awakenings),
        "cry_load": float(f.cry_load),
        "scratch_load": float(f.scratch_load),
        "sleep_fragmentation": float(f.sleep_fragmentation),
        "severity": float(severity),
    }


def write_night(
    f: NightFeatures, severity: float, night_ts: int, out_dir: str = "data/gold/nights"
) -> pathlib.Path:
    """Escribe la noche a out_dir/<night_ts>.parquet y devuelve la ruta."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{int(night_ts)}.parquet"
    pl.DataFrame([night_row(f, severity, night_ts)], schema=_SCHEMA).write_parquet(path)
    return path


def read_nights(out_dir: str = "data/gold/nights") -> pl.DataFrame:
    """Lee todas las noches ordenadas por night_ts. DF vacío con schema si no hay."""
    files = sorted(pathlib.Path(out_dir).glob("*.parquet"))
    if not files:
        return pl.DataFrame(schema=_SCHEMA)
    return pl.concat([pl.read_parquet(f) for f in files]).sort("night_ts")
