"""Factual clinician report MODEL and a pure builder.

This is a data structure, not a PDF. Rendering is an adapter concern (Phase 2
markdown, Phase 4 PDF). The report always cites the exact plan version and
policy version it was built against, and keeps non-prescribed items in their
own section, separate from the prescribed plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .checkin import Observation
from .enums import TreatmentSource
from .ids import DependentId, PlanId, PlanItemId, PlanVersionId, ReportId
from .media import MediaDocument
from .patterns import CandidatePattern
from .plan import MedicalPlan, PlanItem
from .provenance import Provenance
from .treatment import TreatmentMention

DISCLAIMER = (
    "Reporte informativo generado por Lumi. No es un diagnostico ni reemplaza "
    "el criterio del medico tratante. La decision clinica corresponde al medico."
)


@dataclass(frozen=True)
class AdherenceLine:
    plan_item_id: PlanItemId
    instruction_text: str
    observed_count: int


@dataclass(frozen=True)
class EvolutionPoint:
    on: date
    category: str
    note: str


@dataclass(frozen=True)
class PhotoRef:
    media_id: str
    captured_on: date


@dataclass(frozen=True)
class NonPrescribedLine:
    mention_id: str
    text: str


@dataclass(frozen=True)
class CoverageNote:
    topic: str
    status: str  # "present" | "missing"


@dataclass(frozen=True)
class ClinicianReport:
    id: ReportId
    dependent_id: DependentId
    generated_at: datetime
    plan_id: PlanId | None
    plan_version_id: PlanVersionId | None
    plan_version_number: int | None
    policy_version: str
    active_plan_items: tuple[PlanItem, ...]
    symptom_sleep_evolution: tuple[EvolutionPoint, ...]
    adherence: tuple[AdherenceLine, ...]
    candidate_patterns: tuple[CandidatePattern, ...]
    non_prescribed_items: tuple[NonPrescribedLine, ...]
    photos: tuple[PhotoRef, ...]
    coverage_notes: tuple[CoverageNote, ...]
    provenance: Provenance
    disclaimer: str = DISCLAIMER


_EVOLUTION_CATEGORIES = {"sleep", "scratching", "observed_scratching", "irritability"}


def build_clinician_report(
    *,
    report_id: ReportId,
    dependent_id: DependentId,
    plan: MedicalPlan | None,
    mentions: tuple[TreatmentMention, ...],
    observations: tuple[Observation, ...],
    media: tuple[MediaDocument, ...],
    candidate_patterns: tuple[CandidatePattern, ...],
    policy_version: str,
    generated_at: datetime,
    provenance: Provenance,
) -> ClinicianReport:
    """Build a factual report from already-loaded records (pure function)."""
    active = plan.active_version if plan is not None else None
    active_items = active.items if active is not None else ()

    # Adherence: only confirmed prescribed items; count prescribed mentions
    # linked to each item. Non-prescribed contributes zero adherence lines.
    adherence = tuple(
        AdherenceLine(
            plan_item_id=item.id,
            instruction_text=item.instruction_text,
            observed_count=sum(
                1 for m in mentions if m.linked_plan_item_id == item.id
            ),
        )
        for item in active_items
    )

    # Non-prescribed items go in their own section, never merged with the plan.
    non_prescribed = tuple(
        NonPrescribedLine(mention_id=str(m.id), text=m.text)
        for m in mentions
        if m.source is TreatmentSource.NON_PRESCRIBED
    )

    evolution = tuple(
        EvolutionPoint(
            on=o.provenance.recorded_at.date(),
            category=o.category,
            note=o.value_text,
        )
        for o in observations
        if o.category in _EVOLUTION_CATEGORIES
    )

    photos = tuple(
        PhotoRef(media_id=str(m.id), captured_on=m.captured_on)
        for m in sorted(
            (m for m in media if m.kind == "photo"), key=lambda m: m.captured_on
        )
    )

    coverage = (
        CoverageNote("photos", "present" if photos else "missing"),
        CoverageNote("observations", "present" if observations else "missing"),
        CoverageNote("active_plan", "present" if active_items else "missing"),
    )

    return ClinicianReport(
        id=report_id,
        dependent_id=dependent_id,
        generated_at=generated_at,
        plan_id=plan.id if plan is not None else None,
        plan_version_id=active.id if active is not None else None,
        plan_version_number=active.version_number if active is not None else None,
        policy_version=policy_version,
        active_plan_items=active_items,
        symptom_sleep_evolution=evolution,
        adherence=adherence,
        candidate_patterns=candidate_patterns,
        non_prescribed_items=non_prescribed,
        photos=photos,
        coverage_notes=coverage,
        provenance=provenance,
    )
