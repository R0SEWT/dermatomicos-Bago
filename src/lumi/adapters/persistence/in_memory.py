"""In-memory repository and unit of work for development and tests.

The unit of work snapshots the store's containers on entry; an exception or a
block that never commits restores the snapshot (rollback), so a half-activated
plan is impossible. Stored objects are frozen, so shallow container copies are
sufficient for isolation.
"""

from __future__ import annotations

import copy
from types import TracebackType

from ...domain.audit import AuditEvent
from ...domain.checkin import DailyCheckIn, Observation
from ...domain.errors import IdempotencyViolation, NotFoundError
from ...domain.identity import CaregiverAccount, DependentProfile
from ...domain.ids import (
    CaregiverId,
    DependentId,
    PlanId,
    ProposalRef,
    ProviderEventId,
)
from ...domain.media import MediaDocument
from ...domain.plan import MedicalPlan, PlanProposal
from ...domain.safety_decision import SafetyDecision
from ...domain.treatment import TreatmentMention
from ...domain.views import CaregiverExport, DependentTimeline, DeletionReceipt

_CONTAINERS = (
    "caregivers",
    "identity_index",
    "dependents",
    "plans",
    "plan_by_dependent",
    "proposals",
    "rejected_proposals",
    "mentions",
    "checkins",
    "observations",
    "media",
    "safety_decisions",
    "audit",
    "event_results",
)


class InMemoryStore:
    """Backing state shared across units of work."""

    def __init__(self) -> None:
        self.caregivers: dict[CaregiverId, CaregiverAccount] = {}
        self.identity_index: dict[tuple[str, str], CaregiverId] = {}
        self.dependents: dict[DependentId, DependentProfile] = {}
        self.plans: dict[PlanId, MedicalPlan] = {}
        self.plan_by_dependent: dict[DependentId, PlanId] = {}
        self.proposals: dict[ProposalRef, PlanProposal] = {}
        self.rejected_proposals: set[ProposalRef] = set()
        self.mentions: list[TreatmentMention] = []
        self.checkins: list[DailyCheckIn] = []
        self.observations: list[Observation] = []
        self.media: list[MediaDocument] = []
        self.safety_decisions: list[SafetyDecision] = []
        self.audit: list[AuditEvent] = []
        self.event_results: dict[ProviderEventId, str] = {}


class InMemoryRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._s = store

    # identity ---------------------------------------------------------------
    def add_caregiver(self, account: CaregiverAccount) -> None:
        self._s.caregivers[account.id] = account
        for ident in account.identities:
            self._s.identity_index[(ident.channel, ident.opaque_id)] = account.id

    def get_caregiver(self, caregiver_id: CaregiverId) -> CaregiverAccount | None:
        return self._s.caregivers.get(caregiver_id)

    def find_caregiver_by_identity(
        self, channel: str, opaque_id: str
    ) -> CaregiverAccount | None:
        cid = self._s.identity_index.get((channel, opaque_id))
        return self._s.caregivers.get(cid) if cid is not None else None

    def add_dependent(self, profile: DependentProfile) -> None:
        self._s.dependents[profile.id] = profile

    def get_dependent(self, dependent_id: DependentId) -> DependentProfile | None:
        return self._s.dependents.get(dependent_id)

    # plans ------------------------------------------------------------------
    def add_plan(self, plan: MedicalPlan) -> None:
        self._s.plans[plan.id] = plan
        self._s.plan_by_dependent[plan.dependent_id] = plan.id

    def save_plan(self, plan: MedicalPlan) -> None:
        self._s.plans[plan.id] = plan
        self._s.plan_by_dependent[plan.dependent_id] = plan.id

    def get_plan(self, plan_id: PlanId) -> MedicalPlan | None:
        return self._s.plans.get(plan_id)

    def get_plan_for_dependent(self, dependent_id: DependentId) -> MedicalPlan | None:
        pid = self._s.plan_by_dependent.get(dependent_id)
        return self._s.plans.get(pid) if pid is not None else None

    # proposals --------------------------------------------------------------
    def add_proposal(self, ref: ProposalRef, proposal: PlanProposal) -> None:
        self._s.proposals[ref] = proposal

    def get_proposal(self, ref: ProposalRef) -> PlanProposal | None:
        if ref in self._s.rejected_proposals:
            return None
        return self._s.proposals.get(ref)

    def mark_proposal_rejected(self, ref: ProposalRef) -> None:
        self._s.rejected_proposals.add(ref)

    # facts ------------------------------------------------------------------
    def add_treatment_mention(self, mention: TreatmentMention) -> None:
        self._s.mentions.append(mention)

    def add_checkin(self, checkin: DailyCheckIn) -> None:
        self._s.checkins.append(checkin)

    def add_observation(self, observation: Observation) -> None:
        self._s.observations.append(observation)

    def add_media(self, media: MediaDocument) -> None:
        self._s.media.append(media)

    def add_safety_decision(self, decision: SafetyDecision) -> None:
        self._s.safety_decisions.append(decision)

    def timeline_for_dependent(self, dependent_id: DependentId) -> DependentTimeline:
        return DependentTimeline(
            dependent_id=dependent_id,
            mentions=tuple(m for m in self._s.mentions if m.dependent_id == dependent_id),
            checkins=tuple(c for c in self._s.checkins if c.dependent_id == dependent_id),
            observations=tuple(
                o for o in self._s.observations if o.dependent_id == dependent_id
            ),
            media=tuple(m for m in self._s.media if m.dependent_id == dependent_id),
            safety_decisions=tuple(
                d for d in self._s.safety_decisions if d.dependent_id == dependent_id
            ),
        )

    # idempotency ------------------------------------------------------------
    def result_for_provider_event(
        self, provider_event_id: ProviderEventId
    ) -> str | None:
        return self._s.event_results.get(provider_event_id)

    def remember_provider_event(
        self, provider_event_id: ProviderEventId, result_ref: str
    ) -> None:
        existing = self._s.event_results.get(provider_event_id)
        if existing is not None and existing != result_ref:
            raise IdempotencyViolation(
                f"provider event {provider_event_id} already produced {existing}"
            )
        self._s.event_results[provider_event_id] = result_ref

    # audit ------------------------------------------------------------------
    def add_audit(self, event: AuditEvent) -> None:
        self._s.audit.append(event)

    def audit_for_caregiver(self, caregiver_id: CaregiverId) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self._s.audit if e.caregiver_id == caregiver_id)

    # export / deletion ------------------------------------------------------
    def _dependent_ids(self, caregiver_id: CaregiverId) -> set[DependentId]:
        return {
            d.id for d in self._s.dependents.values() if d.caregiver_id == caregiver_id
        }

    def export_caregiver(self, caregiver_id: CaregiverId) -> CaregiverExport:
        caregiver = self._s.caregivers.get(caregiver_id)
        if caregiver is None:
            raise NotFoundError(f"caregiver {caregiver_id} not found")
        dep_ids = self._dependent_ids(caregiver_id)
        return CaregiverExport(
            caregiver=caregiver,
            dependents=tuple(
                d for d in self._s.dependents.values() if d.caregiver_id == caregiver_id
            ),
            plans=tuple(p for p in self._s.plans.values() if p.dependent_id in dep_ids),
            mentions=tuple(m for m in self._s.mentions if m.dependent_id in dep_ids),
            checkins=tuple(c for c in self._s.checkins if c.dependent_id in dep_ids),
            observations=tuple(
                o for o in self._s.observations if o.dependent_id in dep_ids
            ),
            media=tuple(m for m in self._s.media if m.dependent_id in dep_ids),
            safety_decisions=tuple(
                d for d in self._s.safety_decisions if d.dependent_id in dep_ids
            ),
            audit=self.audit_for_caregiver(caregiver_id),
        )

    def delete_caregiver(self, caregiver_id: CaregiverId) -> DeletionReceipt:
        dep_ids = self._dependent_ids(caregiver_id)
        counts: list[tuple[str, int]] = []
        related_refs = {str(caregiver_id), *(str(item) for item in dep_ids)}
        related_plans = [p for p in self._s.plans.values() if p.dependent_id in dep_ids]
        related_refs.update(str(plan.id) for plan in related_plans)
        related_refs.update(
            str(version.id) for plan in related_plans for version in plan.versions
        )
        related_refs.update(
            str(item.id)
            for plan in related_plans
            for version in plan.versions
            for item in version.items
        )
        related_proposals = {
            ref for ref, proposal in self._s.proposals.items()
            if proposal.dependent_id in dep_ids
        }
        related_refs.update(str(ref) for ref in related_proposals)
        for container in (
            self._s.mentions, self._s.checkins, self._s.observations, self._s.media,
            self._s.safety_decisions,
        ):
            related_refs.update(
                str(item.id) for item in container if item.dependent_id in dep_ids
            )

        def drop_list(name: str, container: list) -> None:
            before = len(container)
            container[:] = [x for x in container if x.dependent_id not in dep_ids]
            counts.append((name, before - len(container)))

        drop_list("mentions", self._s.mentions)
        drop_list("checkins", self._s.checkins)
        drop_list("observations", self._s.observations)
        drop_list("media", self._s.media)
        drop_list("safety_decisions", self._s.safety_decisions)

        plans_before = len(self._s.plans)
        self._s.plans = {
            pid: p for pid, p in self._s.plans.items() if p.dependent_id not in dep_ids
        }
        counts.append(("plans", plans_before - len(self._s.plans)))
        for did in dep_ids:
            self._s.plan_by_dependent.pop(did, None)

        counts.append(("dependents", len(dep_ids)))
        for did in dep_ids:
            self._s.dependents.pop(did, None)

        proposals_before = len(self._s.proposals)
        self._s.proposals = {
            ref: proposal for ref, proposal in self._s.proposals.items()
            if ref not in related_proposals
        }
        self._s.rejected_proposals.difference_update(related_proposals)
        counts.append(("proposals", proposals_before - len(self._s.proposals)))

        audit_before = len(self._s.audit)
        self._s.audit[:] = [e for e in self._s.audit if e.caregiver_id != caregiver_id]
        counts.append(("audit", audit_before - len(self._s.audit)))

        for key in list(self._s.identity_index):
            if self._s.identity_index[key] == caregiver_id:
                del self._s.identity_index[key]
        if self._s.caregivers.pop(caregiver_id, None) is not None:
            counts.append(("caregiver", 1))

        events_before = len(self._s.event_results)
        self._s.event_results = {
            event_id: result for event_id, result in self._s.event_results.items()
            if result.partition(":")[2] not in related_refs
        }
        counts.append(("idempotency_events", events_before - len(self._s.event_results)))

        return DeletionReceipt(caregiver_id=caregiver_id, counts=tuple(counts))


class InMemoryUnitOfWork:
    """Atomic unit of work over an ``InMemoryStore`` via snapshot/restore."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self.repo = InMemoryRepository(store)
        self._snapshot: dict[str, object] | None = None
        self._committed = False

    def __enter__(self) -> "InMemoryUnitOfWork":
        self._snapshot = {name: copy.copy(getattr(self._store, name)) for name in _CONTAINERS}
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc is not None or not self._committed:
            self.rollback()
        return False

    def commit(self) -> None:
        self._committed = True
        self._snapshot = None

    def rollback(self) -> None:
        if self._snapshot is not None:
            for name, value in self._snapshot.items():
                setattr(self._store, name, value)
            self._snapshot = None
        self._committed = False
