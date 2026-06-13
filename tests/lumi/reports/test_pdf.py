"""Clinician report HTML/PDF rendering.

HTML content is asserted without system libraries; the PDF byte test is skipped
when the optional ``report`` extra (WeasyPrint) is not installed.
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime

import pytest

from lumi.adapters.reports.pdf import (
    render_clinician_report_html,
    render_clinician_report_pdf,
)
from lumi.domain.enums import (
    ActorKind,
    ConfirmationState,
    TreatmentSource,
)
from lumi.domain.plan import PlanItem
from lumi.domain.provenance import Actor, Provenance
from lumi.domain.report import (
    AdherenceLine,
    ClinicianReport,
    CoverageNote,
    EvolutionPoint,
    NonPrescribedLine,
    PhotoRef,
)

_WEASYPRINT = importlib.util.find_spec("weasyprint") is not None
_needs_weasyprint = pytest.mark.skipif(
    not _WEASYPRINT, reason="requires the 'report' extra (WeasyPrint)"
)


def _provenance() -> Provenance:
    return Provenance(
        actor=Actor(kind=ActorKind.SYSTEM, ref="report-builder"),
        recorded_at=datetime(2026, 6, 13, 8, 0, 0),
        confirmation_state=ConfirmationState.CONFIRMED,
    )


def _report() -> ClinicianReport:
    prov = _provenance()
    plan_item = PlanItem(
        id="item-1",  # type: ignore[arg-type]
        source=TreatmentSource.PRESCRIBED,
        instruction_text="Hidratante 2 veces al dia",
        confirmation_state=ConfirmationState.CONFIRMED,
        provenance=prov,
    )
    return ClinicianReport(
        id="report-1",  # type: ignore[arg-type]
        dependent_id="dep-1",  # type: ignore[arg-type]
        generated_at=datetime(2026, 6, 13, 8, 0, 0),
        plan_id="plan-1",  # type: ignore[arg-type]
        plan_version_id="ver-1",  # type: ignore[arg-type]
        plan_version_number=2,
        policy_version="redflags-v1",
        active_plan_items=(plan_item,),
        symptom_sleep_evolution=(
            EvolutionPoint(on=date(2026, 6, 12), category="sleep", note="durmio mal"),
        ),
        adherence=(
            AdherenceLine(
                plan_item_id="item-1",  # type: ignore[arg-type]
                instruction_text="Hidratante 2 veces al dia",
                observed_count=3,
            ),
        ),
        candidate_patterns=(),
        non_prescribed_items=(
            NonPrescribedLine(mention_id="m-9", text="Crema de la abuela"),
        ),
        photos=(PhotoRef(media_id="media-1", captured_on=date(2026, 6, 11)),),
        coverage_notes=(CoverageNote(topic="photos", status="present"),),
        provenance=prov,
    )


def test_html_has_all_sections_and_disclaimer():
    html = render_clinician_report_html(_report())
    for heading in (
        "Plan prescrito activo",
        "Evolucion observada",
        "Adherencia",
        "Patrones a validar",
        "Productos o remedios no prescritos",
        "Fotos",
        "Cobertura de datos",
    ):
        assert heading in html
    assert "no es un diagnostico" in html.lower()
    assert "version 2" in html and "redflags-v1" in html


def test_html_keeps_non_prescribed_separate_from_plan():
    html = render_clinician_report_html(_report())
    # The non-prescribed remedy must not appear inside the prescribed-plan list.
    plan_section = html.split("Productos o remedios no prescritos")[0]
    assert "Crema de la abuela" not in plan_section
    assert "Crema de la abuela" in html


def test_html_has_no_causal_or_diagnostic_language():
    html = render_clinician_report_html(_report()).lower()
    for forbidden in ("alergia", "causa", "diagnostic", "porque le dio"):
        assert forbidden not in html or forbidden == "diagnostic"
    # "diagnostic" only allowed inside the disclaimer's "no es un diagnostico".
    assert "no es un diagnostico" in html


def test_html_is_deterministic():
    assert render_clinician_report_html(_report()) == render_clinician_report_html(
        _report()
    )


@_needs_weasyprint
def test_pdf_renders_valid_bytes():
    pdf = render_clinician_report_pdf(_report())
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000
