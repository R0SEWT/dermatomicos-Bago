"""AI extraction port and untrusted proposal DTOs (stdlib only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..domain.enums import TreatmentSource


@dataclass(frozen=True)
class VersionStamp:
    deployment: str
    model_version: str
    api_version: str
    schema_version: str
    prompt_version: str
    eval_set_version: str


@dataclass(frozen=True)
class ExtractionContext:
    correlation_id: str
    dependent_age_months: int | None = None
    active_plan_summary: str | None = None
    locale: str = "es-PE"


@dataclass(frozen=True)
class ProposedPlanItem:
    description: str
    source: TreatmentSource | None
    verbatim_span: str
    confidence: float
    ambiguous_source: bool
    dose_instructions: str | None = None
    cadence_hint: str | None = None


@dataclass(frozen=True)
class AIPlanProposal:
    items: tuple[ProposedPlanItem, ...]
    version: VersionStamp
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposedObservation:
    category: str
    value_text: str
    verbatim_span: str
    confidence: float
    treatment_source: TreatmentSource | None
    ambiguous_source: bool


@dataclass(frozen=True)
class ProposedSafetySignals:
    age_months: int | None = None
    fever_c: float | None = None
    lethargy: bool = False
    poor_feeding: bool = False
    spreading_rash: bool = False
    rash_with_pus_or_blisters: bool = False
    breathing_difficulty: bool = False
    inconsolable_crying: bool = False


@dataclass(frozen=True)
class ObservationProposal:
    observations: tuple[ProposedObservation, ...]
    signals: ProposedSafetySignals
    version: VersionStamp
    warnings: tuple[str, ...] = ()


class AIExtractionPort(Protocol):
    def extract_plan_proposal(
        self, text: str, context: ExtractionContext
    ) -> AIPlanProposal: ...

    def extract_daily_observations(
        self, text: str, context: ExtractionContext
    ) -> ObservationProposal: ...
