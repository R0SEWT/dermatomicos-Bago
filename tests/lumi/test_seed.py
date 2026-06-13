"""The demo seed produces a rich, deterministic scenario (no AI, no network)."""

from lumi.api.bootstrap import build_runtime
from lumi.api.seed import seed_demo
from lumi.application.commands import BuildClinicianReport, ExportCaregiverData
from lumi.domain.enums import SafetyDisposition, TreatmentSource
from lumi.domain.patterns import PatternTemplate


def _seeded():
    runtime = build_runtime(use_ai=False)
    result = seed_demo(runtime)
    return runtime, result


def test_seed_sets_session_profile():
    runtime, result = _seeded()
    assert runtime.session.caregiver_id == result.caregiver_id
    assert runtime.session.dependent_id == result.dependent_id


def test_seed_produces_repeated_after_pattern():
    runtime, result = _seeded()
    report = runtime.application.build_clinician_report(
        BuildClinicianReport(result.dependent_id)
    )
    repeated = [
        p for p in report.candidate_patterns
        if p.template is PatternTemplate.REPEATED_AFTER
    ]
    assert repeated, "the seed must trigger at least one repeated-after pattern"
    assert all(p.status == "to_validate" for p in report.candidate_patterns)
    assert any("jabón nuevo" in p.rendered for p in repeated)


def test_seed_has_adherence_non_prescribed_and_safety_event():
    runtime, result = _seeded()
    app = runtime.application
    report = app.build_clinician_report(BuildClinicianReport(result.dependent_id))
    export = app.export_caregiver_data(ExportCaregiverData(result.caregiver_id))

    assert max(line.observed_count for line in report.adherence) >= 3
    assert report.non_prescribed_items
    assert all(
        m.source is TreatmentSource.NON_PRESCRIBED
        for m in export.mentions if "manzanilla" in m.text
    )
    dispositions = {d.evaluation.disposition for d in export.safety_decisions}
    assert SafetyDisposition.CONTACT_CLINICIAN in dispositions
    # The latest check-in is reassuring (green), so the panel opens calm.
    assert export.safety_decisions[-1].evaluation.disposition is (
        SafetyDisposition.CONTINUE_RECORDING
    )


def test_seed_transcript_ends_on_magic_moment():
    _, result = _seeded()
    assert result.transcript
    assert "patrón para validar" in result.transcript[-1].text
    assert result.transcript[-1].role == "lumi"
