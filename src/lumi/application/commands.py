"""Command objects, one per use case. All frozen; mutating ones carry an event id."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.enums import TreatmentSource
from ..domain.ids import (
    CaregiverId,
    DependentId,
    PlanItemId,
    ProposalRef,
    ProviderEventId,
)
from ..domain.plan import PlanProposal
from ..domain.provenance import Actor, ExternalIdentity
from ..domain.signals import ObservationSignals


@dataclass(frozen=True)
class RegisterCaregiver:
    identity: ExternalIdentity
    locale: str = "es-PE"
    provider_event_id: ProviderEventId | None = None


@dataclass(frozen=True)
class RegisterDependent:
    caregiver_id: CaregiverId
    alias: str
    birth_month: str | None = None
    provider_event_id: ProviderEventId | None = None


@dataclass(frozen=True)
class ProposeMedicalPlan:
    proposal: PlanProposal
    provider_event_id: ProviderEventId | None = None


@dataclass(frozen=True)
class ConfirmMedicalPlanVersion:
    dependent_id: DependentId
    proposal_ref: ProposalRef
    confirmed_item_indexes: tuple[int, ...]
    actor: Actor
    provider_event_id: ProviderEventId | None = None


@dataclass(frozen=True)
class RejectMedicalPlanProposal:
    proposal_ref: ProposalRef
    actor: Actor
    provider_event_id: ProviderEventId | None = None


@dataclass(frozen=True)
class RecordTreatmentMention:
    dependent_id: DependentId
    source: TreatmentSource
    text: str
    linked_plan_item_id: PlanItemId | None = None
    source_message_id: str | None = None
    provider_event_id: ProviderEventId | None = None


@dataclass(frozen=True)
class RecordCheckIn:
    dependent_id: DependentId
    note_text: str
    observations: tuple[tuple[str, str], ...] = ()
    signals: ObservationSignals = field(default_factory=ObservationSignals)
    source_message_id: str | None = None
    provider_event_id: ProviderEventId | None = None


@dataclass(frozen=True)
class BuildClinicianReport:
    dependent_id: DependentId


@dataclass(frozen=True)
class ExportCaregiverData:
    caregiver_id: CaregiverId


@dataclass(frozen=True)
class DeleteCaregiverData:
    caregiver_id: CaregiverId
    actor: Actor
    provider_event_id: ProviderEventId | None = None
