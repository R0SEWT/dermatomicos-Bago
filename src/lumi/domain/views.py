"""Read-model views returned by the repository (timeline, export, deletion)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .audit import AuditEvent
from .checkin import DailyCheckIn, Observation
from .identity import CaregiverAccount, DependentProfile
from .ids import CaregiverId, DependentId
from .media import MediaDocument
from .plan import MedicalPlan
from .safety_decision import SafetyDecision
from .treatment import TreatmentMention


@dataclass(frozen=True)
class DependentTimeline:
    dependent_id: DependentId
    mentions: tuple[TreatmentMention, ...] = ()
    checkins: tuple[DailyCheckIn, ...] = ()
    observations: tuple[Observation, ...] = ()
    media: tuple[MediaDocument, ...] = ()
    safety_decisions: tuple[SafetyDecision, ...] = ()


@dataclass(frozen=True)
class CaregiverExport:
    caregiver: CaregiverAccount
    dependents: tuple[DependentProfile, ...] = ()
    plans: tuple[MedicalPlan, ...] = ()
    mentions: tuple[TreatmentMention, ...] = ()
    checkins: tuple[DailyCheckIn, ...] = ()
    observations: tuple[Observation, ...] = ()
    media: tuple[MediaDocument, ...] = ()
    safety_decisions: tuple[SafetyDecision, ...] = ()
    audit: tuple[AuditEvent, ...] = ()


@dataclass(frozen=True)
class DeletionReceipt:
    caregiver_id: CaregiverId
    counts: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    @property
    def total(self) -> int:
        return sum(n for _, n in self.counts)
