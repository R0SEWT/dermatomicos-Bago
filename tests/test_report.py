from dermatomicos_bago.pipeline.report import ReportBuilder
from dermatomicos_bago.pipeline.features import NightFeatures
from dermatomicos_bago.pipeline.severity import SeverityTracker
from dermatomicos_bago.config import SeverityConfig


def test_report_contains_key_metrics_and_disclaimer():
    f = NightFeatures(28800, 600, 5, 300, 8, 27000, 4)
    t = SeverityTracker(SeverityConfig())
    t.update(f.cry_load, f.scratch_load)
    md = ReportBuilder().build(f, t)
    assert "Llanto" in md and "Rascado" in md and "Severidad" in md
    assert "no es un diagnóstico" in md.lower()


def test_escalation_flag_when_severity_high():
    f = NightFeatures(28800, 8000, 30, 9000, 40, 5000, 12)
    t = SeverityTracker(SeverityConfig())
    for _ in range(5):
        t.update(f.cry_load, f.scratch_load)
    md = ReportBuilder().build(f, t)
    assert "Escalada" in md
