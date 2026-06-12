"""Curva de severidad multi-noche (narrativa EczemaPred) — lógica pura + render.

La curva es **path-dependent**: se recompone replayando un solo `SeverityTracker`
sobre los `(cry_load, scratch_load)` de las noches en orden. La severidad que se
guarda por noche en el parquet (tracker fresco, un solo update) es informativa; la
curva acumulada NO la usa, la recalcula al vuelo. Así funciona igual para noches
reales y sintéticas.
"""

import random

from ..config import SeverityConfig
from .features import NightFeatures
from .severity import SeverityTracker

_BLOCKS = "▁▂▃▄▅▆▇█"


def severity_curve(
    loads: list[tuple[float, float]], cfg: SeverityConfig | None = None
) -> list[float]:
    """Replay de un solo tracker sobre las noches en orden -> trayectoria de severidad.

    `loads` es una secuencia de `(cry_load, scratch_load)` por noche, ya ordenada.
    Devuelve `tracker.history` (un valor de severidad acumulada por noche).
    """
    tracker = SeverityTracker(cfg or SeverityConfig())
    for cry_load, scratch_load in loads:
        tracker.update(cry_load, scratch_load)
    return tracker.history


def sparkline(values: list[float], lo: float = 0.0, hi: float = 1.0) -> str:
    """Mapea cada valor a un bloque unicode ▁..█. Puro, sin dependencias de render."""
    if not values:
        return ""
    span = hi - lo
    out = []
    for v in values:
        frac = 0.0 if span <= 0 else (v - lo) / span
        frac = min(1.0, max(0.0, frac))
        idx = round(frac * (len(_BLOCKS) - 1))
        out.append(_BLOCKS[idx])
    return "".join(out)


def synthetic_nights(n: int = 7, seed: int = 0) -> list[NightFeatures]:
    """Secuencia ilustrativa sucias→limpias→recaída (determinista por `seed`).

    Fabrica `NightFeatures` reales con un perfil de carga en forma de U invertida-
    invertida: arranca alto (brote), baja a limpio, recae al final. El jitter es
    leve y reproducible. Pensado para el demo: es una *trayectoria ilustrativa*,
    no datos de cohorte.
    """
    rng = random.Random(seed)
    night_s = 8 * 3600.0  # noche de 8h
    # perfil base de carga total (cry+scratch) por noche, 0..1
    profile = [0.85, 0.65, 0.35, 0.10, 0.05, 0.45, 0.80]
    if n != len(profile):
        # reescala el perfil a n puntos por interpolación lineal simple
        profile = [
            profile[round(i * (len(profile) - 1) / max(1, n - 1))] for i in range(n)
        ]
    nights = []
    for load in profile:
        jitter = rng.uniform(-0.04, 0.04)
        total = min(0.95, max(0.0, load + jitter))
        # repartimos la carga: ~40% llanto, ~60% rascado (como los pesos del config)
        cry_s = total * 0.4 * night_s
        scr_s = total * 0.6 * night_s
        awakenings = round(total * 8)
        quiet_s = max(0.0, night_s - cry_s - scr_s)
        nights.append(
            NightFeatures(
                night_seconds=night_s,
                cry_seconds=cry_s,
                cry_events=max(0, round(total * 6)),
                scratch_seconds=scr_s,
                scratch_events=max(0, round(total * 10)),
                quiet_seconds=quiet_s,
                awakenings=awakenings,
            )
        )
    return nights


def build_trend_report(
    nights: list[NightFeatures],
    curve: list[float],
    cfg: SeverityConfig | None = None,
    escalation_threshold: float = 0.5,
    synthetic: bool = False,
) -> str:
    """Reporte markdown multi-noche: sparkline + tabla por noche + nota de escalada."""
    cfg = cfg or SeverityConfig()
    spark = sparkline(curve, lo=0.0, hi=cfg.max_value)
    latest = curve[-1] if curve else 0.0
    escalated = latest >= escalation_threshold

    illustrative = (
        "> ℹ️ _Trayectoria **ilustrativa** (datos sintéticos) — no afirma predicción "
        "longitudinal; muestra cómo el acumulador reacciona a una secuencia de noches._\n\n"
        if synthetic else ""
    )
    flag = (
        "> ⚠️ **Escalada de brote en la última noche** — considera registrarlo para tu "
        "consulta dermatológica.\n\n"
        if escalated else ""
    )

    rows = []
    for i, (f, sev) in enumerate(zip(nights, curve), start=1):
        rows.append(
            f"| {i} | {f.cry_load:.2f} | {f.scratch_load:.2f} | {f.awakenings} | {sev:.2f} |"
        )
    table = "\n".join(rows)

    return f"""# Tendencia nocturna multi-noche — dermatomicos

{illustrative}{flag}**Curva de severidad** ({len(curve)} noches): `{spark}`  →  actual **{latest:.2f}** / {cfg.max_value:.2f}

| Noche | Carga llanto | Carga rascado | Despertares | Severidad acumulada |
|---|---|---|---|---|
{table}

_Severidad = instancia mínima del framework EczemaPred (acumulador con decay sobre la carga acústica). La curva se recompone replayando un solo acumulador sobre las noches en orden._

---
_Medición acústica objetiva, **no es un diagnóstico**. Consulta a tu dermatólogo._
"""
