"""Medical plan: the immutable, versioned, doctor-authored record.

Two type families that cannot be confused:

* Proposal types (``PlanProposal`` / ``ProposedPlanItem``) are inert untrusted
  data. They have no id, no version, no confirmed flag, and no method that
  activates anything. A model (or a caregiver) may produce a proposal.
* Active types (``PlanItem`` / ``MedicalPlanVersion`` / ``MedicalPlan``) are
  authoritative and immutable. They are only ever constructed by the
  application's explicit caregiver-confirmation path.

Invariants enforced here:

* A non-prescribed item can never carry an adherence schedule.
* Only confirmed, prescribed items belong inside a plan version.
* Editing a plan creates a brand-new version; old versions stay byte-identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .enums import ConfirmationState, TreatmentSource
from .errors import (
    NonPrescribedCannotScheduleError,
    NonPrescribedInVersionError,
    PlanVersionConflictError,
    UnconfirmedItemInVersionError,
)
from .ids import DependentId, PlanId, PlanItemId, PlanVersionId
from .provenance import Actor, Provenance


# --- Proposal types (untrusted, never authoritative) -----------------------


@dataclass(frozen=True)
class ProposedPlanItem:
    """A candidate plan item. ``schedule_hint`` is free text, not a schedule."""

    source: TreatmentSource
    instruction_text: str
    schedule_hint: str | None = None


@dataclass(frozen=True)
class PlanProposal:
    """An inert proposal handed to the application. No id, no activation path."""

    dependent_id: DependentId
    items: tuple[ProposedPlanItem, ...]
    provenance: Provenance


# --- Active types (authoritative, immutable) --------------------------------


@dataclass(frozen=True)
class AdherenceSchedule:
    """A reminder cadence. Only prescribed items may hold one."""

    times_per_day: int
    note: str | None = None


@dataclass(frozen=True)
class PlanItem:
    """A confirmed item inside a plan version."""

    id: PlanItemId
    source: TreatmentSource
    instruction_text: str
    confirmation_state: ConfirmationState
    provenance: Provenance
    adherence_schedule: AdherenceSchedule | None = None

    def __post_init__(self) -> None:
        if (
            self.source is TreatmentSource.NON_PRESCRIBED
            and self.adherence_schedule is not None
        ):
            raise NonPrescribedCannotScheduleError(
                "non_prescribed items cannot carry an adherence schedule"
            )


@dataclass(frozen=True)
class MedicalPlanVersion:
    """An immutable snapshot of the confirmed plan at a point in time."""

    id: PlanVersionId
    plan_id: PlanId
    version_number: int
    items: tuple[PlanItem, ...]
    confirmed_by: Actor
    confirmed_at: datetime
    provenance: Provenance
    supersedes: PlanVersionId | None = None

    def __post_init__(self) -> None:
        for item in self.items:
            if item.confirmation_state is not ConfirmationState.CONFIRMED:
                raise UnconfirmedItemInVersionError(
                    "a plan version may only contain confirmed items"
                )
            if item.source is not TreatmentSource.PRESCRIBED:
                raise NonPrescribedInVersionError(
                    "only prescribed items belong inside a plan version"
                )


@dataclass(frozen=True)
class MedicalPlan:
    """The append-only history of plan versions for one dependent."""

    id: PlanId
    dependent_id: DependentId
    provenance: Provenance
    versions: tuple[MedicalPlanVersion, ...] = ()
    active_version_id: PlanVersionId | None = None

    @property
    def active_version(self) -> MedicalPlanVersion | None:
        if self.active_version_id is None:
            return None
        for version in self.versions:
            if version.id == self.active_version_id:
                return version
        return None

    @property
    def next_version_number(self) -> int:
        return max((v.version_number for v in self.versions), default=0) + 1

    def with_new_version(self, version: MedicalPlanVersion) -> "MedicalPlan":
        """Return a NEW plan with ``version`` appended and made active.

        Never mutates: the previous versions tuple is preserved unchanged.
        """
        if version.version_number != self.next_version_number:
            raise PlanVersionConflictError(
                f"expected version {self.next_version_number}, got {version.version_number}"
            )
        if version.supersedes != self.active_version_id:
            raise PlanVersionConflictError(
                "new version must supersede the current active version"
            )
        return MedicalPlan(
            id=self.id,
            dependent_id=self.dependent_id,
            provenance=self.provenance,
            versions=(*self.versions, version),
            active_version_id=version.id,
        )
