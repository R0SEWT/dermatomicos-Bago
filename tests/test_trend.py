from dermatomicos_bago.config import SeverityConfig
from dermatomicos_bago.pipeline.severity import SeverityTracker
from dermatomicos_bago.pipeline.trend import (
    severity_curve,
    sparkline,
    synthetic_nights,
    build_trend_report,
)


def test_severity_curve_matches_manual_replay():
    loads = [(0.8, 0.7), (0.1, 0.05), (0.0, 0.0), (0.6, 0.5)]
    cfg = SeverityConfig()
    t = SeverityTracker(cfg)
    expected = [t.update(c, s) for c, s in loads]
    assert severity_curve(loads, cfg) == expected


def test_sparkline_empty_and_extremes():
    assert sparkline([]) == ""
    # un solo char por valor
    assert len(sparkline([0.1, 0.5, 0.9])) == 3
    # min -> ▁, max -> █
    spark = sparkline([0.0, 1.0], lo=0.0, hi=1.0)
    assert spark[0] == "▁" and spark[1] == "█"


def test_sparkline_constant_values_same_char():
    spark = sparkline([0.5, 0.5, 0.5])
    assert len(set(spark)) == 1


def test_synthetic_nights_deterministic_and_shaped():
    a = synthetic_nights(7, seed=0)
    b = synthetic_nights(7, seed=0)
    assert len(a) == 7
    # determinista
    assert [n.cry_seconds for n in a] == [n.cry_seconds for n in b]
    loads = [n.cry_load + n.scratch_load for n in a]
    # forma sucias -> limpias -> recaída: arranca alto, hay un mínimo intermedio, sube al final
    assert loads[0] > min(loads)
    assert loads[-1] > min(loads)
    assert min(loads) == min(loads[1:-1])


def test_build_trend_report_contents():
    nights = synthetic_nights(7, seed=0)
    loads = [(n.cry_load, n.scratch_load) for n in nights]
    curve = severity_curve(loads)
    md = build_trend_report(nights, curve, synthetic=True)
    assert "Curva de severidad" in md
    assert "ilustrativa" in md  # disclaimer sintético
    # tabla con una fila por noche
    assert md.count("\n| 1 |") == 1


def test_build_trend_report_escalation_flag():
    # noches muy sucias -> última severidad alta -> flag de escalada
    loads = [(1.0, 1.0)] * 5
    curve = severity_curve(loads)
    nights = synthetic_nights(5, seed=1)
    md = build_trend_report(nights, curve, escalation_threshold=0.5)
    assert "Escalada" in md


def test_build_trend_report_non_synthetic_omits_disclaimer():
    nights = synthetic_nights(7, seed=0)
    curve = severity_curve([(n.cry_load, n.scratch_load) for n in nights])
    md = build_trend_report(nights, curve, synthetic=False)
    assert "ilustrativa" not in md


def test_build_trend_report_no_escalation_when_below_threshold():
    # noches limpias -> severidad baja -> sin bloque de escalada
    loads = [(0.0, 0.0)] * 5
    curve = severity_curve(loads)
    nights = synthetic_nights(5, seed=1)
    md = build_trend_report(nights, curve, escalation_threshold=0.5)
    assert "Escalada" not in md
