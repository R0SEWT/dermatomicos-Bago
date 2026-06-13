"""Deterministic use-case orchestration for Lumi."""

from __future__ import annotations

from collections.abc import Callable

from ..domain.audit import AuditEvent
from ..domain.checkin import DailyCheckIn, Observation
from ..domain.enums import ActorKind, AuditAction, ConfirmationState, TreatmentSource
from ..domain.errors import IdempotencyViolation, NotFoundError, OwnershipError, ProposalCannotActivateError
from ..domain.identity import CaregiverAccount, DependentProfile
from ..domain.ids import (
    AuditId, CaregiverId, CheckInId, DependentId, MentionId, ObservationId,
    PlanId, PlanItemId, PlanVersionId, ProposalRef, ProviderEventId, ReportId,
    SafetyDecisionId,
)
from ..domain.plan import MedicalPlan, MedicalPlanVersion, PlanItem
from ..domain.provenance import Actor, Provenance
from ..domain.report import ClinicianReport, build_clinician_report
from ..domain.safety_decision import SafetyDecision
from ..domain.treatment import TreatmentMention
from ..domain.views import CaregiverExport, DeletionReceipt
from ..ports.clock import Clock
from ..ports.ids import IdGenerator
from ..ports.policy import SafetyPolicy
from ..ports.repository import Repository, UnitOfWork
from .commands import (
    BuildClinicianReport, ConfirmMedicalPlanVersion, DeleteCaregiverData,
    ExportCaregiverData, ProposeMedicalPlan, RecordCheckIn, RecordTreatmentMention,
    RegisterCaregiver, RegisterDependent, RejectMedicalPlanProposal,
)
from .results import CheckInResult

UnitOfWorkFactory = Callable[[], UnitOfWork]


class LumiApplication:
    """Coordinates transactions without depending on vendor SDKs."""

    def __init__(
        self, uow_factory: UnitOfWorkFactory, clock: Clock, ids: IdGenerator,
        policy: SafetyPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._policy = policy

    def _id(self, id_type, prefix: str):
        return id_type(self._ids.new(prefix))

    def _provenance(
        self, actor: Actor, state: ConfirmationState, *,
        provider_event_id: ProviderEventId | None = None,
        source_message_id: str | None = None,
    ) -> Provenance:
        return Provenance(
            actor=actor, recorded_at=self._clock.now(), confirmation_state=state,
            source_message_id=source_message_id, provider_event_id=provider_event_id,
        )

    @staticmethod
    def _replay(
        repo: Repository, event_id: ProviderEventId | None, expected_kind: str,
    ) -> str | None:
        if event_id is None:
            return None
        existing = repo.result_for_provider_event(event_id)
        if existing is None:
            return None
        kind, separator, ref = existing.partition(":")
        if not separator or kind != expected_kind:
            raise IdempotencyViolation(
                f"provider event {event_id} was already used for {kind or existing}"
            )
        return ref

    @staticmethod
    def _remember(
        repo: Repository, event_id: ProviderEventId | None, kind: str, ref: str,
    ) -> None:
        if event_id is not None:
            repo.remember_provider_event(event_id, f"{kind}:{ref}")

    def _audit(
        self, repo: Repository, *, action: AuditAction, caregiver_id: CaregiverId,
        subject_ref: str, provenance: Provenance,
        detail: tuple[tuple[str, str], ...] = (),
    ) -> None:
        repo.add_audit(AuditEvent(
            id=self._id(AuditId, "audit"), action=action, caregiver_id=caregiver_id,
            subject_ref=subject_ref, provenance=provenance, detail=detail,
        ))

    @staticmethod
    def _dependent_and_owner(
        repo: Repository, dependent_id: DependentId,
    ) -> tuple[DependentProfile, CaregiverId]:
        dependent = repo.get_dependent(dependent_id)
        if dependent is None:
            raise NotFoundError(f"dependent {dependent_id} not found")
        return dependent, dependent.caregiver_id

    @staticmethod
    def _require_owner(actor: Actor, caregiver_id: CaregiverId) -> None:
        if actor.kind is not ActorKind.CAREGIVER:
            raise ProposalCannotActivateError("only a caregiver may activate a plan")
        if actor.ref != str(caregiver_id):
            raise OwnershipError("caregiver actor does not own this dependent")

    def register_caregiver(self, command: RegisterCaregiver) -> CaregiverId:
        with self._uow_factory() as uow:
            replay = self._replay(uow.repo, command.provider_event_id, "caregiver")
            if replay is not None:
                return CaregiverId(replay)
            existing = uow.repo.find_caregiver_by_identity(
                command.identity.channel, command.identity.opaque_id
            )
            if existing is not None:
                return existing.id
            caregiver_id = self._id(CaregiverId, "caregiver")
            actor = Actor(ActorKind.CAREGIVER, str(caregiver_id))
            provenance = self._provenance(
                actor, ConfirmationState.CONFIRMED,
                provider_event_id=command.provider_event_id,
            )
            uow.repo.add_caregiver(CaregiverAccount(
                id=caregiver_id, identities=(command.identity,), locale=command.locale,
                provenance=provenance,
            ))
            self._audit(
                uow.repo, action=AuditAction.ACCOUNT_CREATED,
                caregiver_id=caregiver_id, subject_ref=str(caregiver_id),
                provenance=provenance,
            )
            self._remember(uow.repo, command.provider_event_id, "caregiver", str(caregiver_id))
            uow.commit()
            return caregiver_id

    def register_dependent(self, command: RegisterDependent) -> DependentId:
        with self._uow_factory() as uow:
            replay = self._replay(uow.repo, command.provider_event_id, "dependent")
            if replay is not None:
                return DependentId(replay)
            if uow.repo.get_caregiver(command.caregiver_id) is None:
                raise NotFoundError(f"caregiver {command.caregiver_id} not found")
            dependent_id = self._id(DependentId, "dependent")
            actor = Actor(ActorKind.CAREGIVER, str(command.caregiver_id))
            provenance = self._provenance(
                actor, ConfirmationState.CONFIRMED,
                provider_event_id=command.provider_event_id,
            )
            uow.repo.add_dependent(DependentProfile(
                id=dependent_id, caregiver_id=command.caregiver_id,
                alias=command.alias, birth_month=command.birth_month,
                provenance=provenance,
            ))
            self._audit(
                uow.repo, action=AuditAction.DEPENDENT_CREATED,
                caregiver_id=command.caregiver_id, subject_ref=str(dependent_id),
                provenance=provenance,
            )
            self._remember(uow.repo, command.provider_event_id, "dependent", str(dependent_id))
            uow.commit()
            return dependent_id

    def propose_medical_plan(self, command: ProposeMedicalPlan) -> ProposalRef:
        with self._uow_factory() as uow:
            replay = self._replay(uow.repo, command.provider_event_id, "proposal")
            if replay is not None:
                return ProposalRef(replay)
            _, caregiver_id = self._dependent_and_owner(uow.repo, command.proposal.dependent_id)
            proposal_ref = self._id(ProposalRef, "proposal")
            uow.repo.add_proposal(proposal_ref, command.proposal)
            self._audit(
                uow.repo, action=AuditAction.PLAN_PROPOSED,
                caregiver_id=caregiver_id, subject_ref=str(proposal_ref),
                provenance=command.proposal.provenance,
            )
            self._remember(uow.repo, command.provider_event_id, "proposal", str(proposal_ref))
            uow.commit()
            return proposal_ref

    def confirm_medical_plan(self, command: ConfirmMedicalPlanVersion) -> PlanVersionId:
        with self._uow_factory() as uow:
            replay = self._replay(uow.repo, command.provider_event_id, "plan_version")
            if replay is not None:
                return PlanVersionId(replay)
            dependent, caregiver_id = self._dependent_and_owner(uow.repo, command.dependent_id)
            self._require_owner(command.actor, caregiver_id)
            proposal = uow.repo.get_proposal(command.proposal_ref)
            if proposal is None:
                raise NotFoundError(f"proposal {command.proposal_ref} not found")
            if proposal.dependent_id != dependent.id:
                raise OwnershipError("proposal belongs to another dependent")
            indexes = tuple(dict.fromkeys(command.confirmed_item_indexes))
            if not indexes or any(i < 0 or i >= len(proposal.items) for i in indexes):
                raise ValueError("confirmed item indexes must reference proposal items")
            selected = tuple(proposal.items[i] for i in indexes)
            if any(item.source is not TreatmentSource.PRESCRIBED for item in selected):
                raise ValueError("non-prescribed items cannot enter a plan version")
            provenance = self._provenance(
                command.actor, ConfirmationState.CONFIRMED,
                provider_event_id=command.provider_event_id,
                source_message_id=proposal.provenance.source_message_id,
            )
            plan = uow.repo.get_plan_for_dependent(dependent.id)
            if plan is None:
                plan = MedicalPlan(
                    id=self._id(PlanId, "plan"), dependent_id=dependent.id,
                    provenance=provenance,
                )
            items = tuple(PlanItem(
                id=self._id(PlanItemId, "plan_item"),
                source=TreatmentSource.PRESCRIBED,
                instruction_text=item.instruction_text,
                confirmation_state=ConfirmationState.CONFIRMED,
                provenance=provenance,
            ) for item in selected)
            version = MedicalPlanVersion(
                id=self._id(PlanVersionId, "plan_version"), plan_id=plan.id,
                version_number=plan.next_version_number, items=items,
                confirmed_by=command.actor, confirmed_at=self._clock.now(),
                provenance=provenance, supersedes=plan.active_version_id,
            )
            activated = plan.with_new_version(version)
            if plan.versions:
                uow.repo.save_plan(activated)
            else:
                uow.repo.add_plan(activated)
            self._audit(
                uow.repo, action=AuditAction.PLAN_CONFIRMED,
                caregiver_id=caregiver_id, subject_ref=str(version.id),
                provenance=provenance,
                detail=(("version", str(version.version_number)),),
            )
            self._remember(
                uow.repo, command.provider_event_id, "plan_version", str(version.id)
            )
            uow.commit()
            return version.id

    def reject_medical_plan(self, command: RejectMedicalPlanProposal) -> ProposalRef:
        with self._uow_factory() as uow:
            replay = self._replay(uow.repo, command.provider_event_id, "rejected_proposal")
            if replay is not None:
                return ProposalRef(replay)
            proposal = uow.repo.get_proposal(command.proposal_ref)
            if proposal is None:
                raise NotFoundError(f"proposal {command.proposal_ref} not found")
            _, caregiver_id = self._dependent_and_owner(uow.repo, proposal.dependent_id)
            self._require_owner(command.actor, caregiver_id)
            provenance = self._provenance(
                command.actor, ConfirmationState.REJECTED,
                provider_event_id=command.provider_event_id,
                source_message_id=proposal.provenance.source_message_id,
            )
            uow.repo.mark_proposal_rejected(command.proposal_ref)
            self._audit(
                uow.repo, action=AuditAction.PLAN_REJECTED,
                caregiver_id=caregiver_id, subject_ref=str(command.proposal_ref),
                provenance=provenance,
            )
            self._remember(
                uow.repo, command.provider_event_id, "rejected_proposal",
                str(command.proposal_ref),
            )
            uow.commit()
            return command.proposal_ref

    def record_treatment_mention(self, command: RecordTreatmentMention) -> MentionId:
        with self._uow_factory() as uow:
            replay = self._replay(uow.repo, command.provider_event_id, "mention")
            if replay is not None:
                return MentionId(replay)
            _, caregiver_id = self._dependent_and_owner(uow.repo, command.dependent_id)
            actor = Actor(ActorKind.CAREGIVER, str(caregiver_id))
            provenance = self._provenance(
                actor, ConfirmationState.CONFIRMED,
                provider_event_id=command.provider_event_id,
                source_message_id=command.source_message_id,
            )
            mention = TreatmentMention(
                id=self._id(MentionId, "mention"), dependent_id=command.dependent_id,
                source=command.source, text=command.text,
                linked_plan_item_id=command.linked_plan_item_id,
                provenance=provenance,
            )
            if command.linked_plan_item_id is not None:
                plan = uow.repo.get_plan_for_dependent(command.dependent_id)
                active_items = plan.active_version.items if plan and plan.active_version else ()
                if command.linked_plan_item_id not in {item.id for item in active_items}:
                    raise NotFoundError("linked plan item is not active for this dependent")
            uow.repo.add_treatment_mention(mention)
            self._audit(
                uow.repo, action=AuditAction.MENTION_RECORDED,
                caregiver_id=caregiver_id, subject_ref=str(mention.id),
                provenance=provenance, detail=(("source", command.source.value),),
            )
            self._remember(uow.repo, command.provider_event_id, "mention", str(mention.id))
            uow.commit()
            return mention.id

    def record_checkin(self, command: RecordCheckIn) -> CheckInResult:
        with self._uow_factory() as uow:
            replay = self._replay(uow.repo, command.provider_event_id, "checkin")
            if replay is not None:
                timeline = uow.repo.timeline_for_dependent(command.dependent_id)
                checkin = next((c for c in timeline.checkins if str(c.id) == replay), None)
                decision = next((
                    d for d in timeline.safety_decisions
                    if d.provenance.provider_event_id == command.provider_event_id
                ), None)
                if checkin is None or decision is None:
                    raise IdempotencyViolation("stored check-in result is incomplete")
                return CheckInResult(checkin.id, decision.id, decision.evaluation)
            _, caregiver_id = self._dependent_and_owner(uow.repo, command.dependent_id)
            actor = Actor(ActorKind.CAREGIVER, str(caregiver_id))
            provenance = self._provenance(
                actor, ConfirmationState.CONFIRMED,
                provider_event_id=command.provider_event_id,
                source_message_id=command.source_message_id,
            )
            observations = tuple(Observation(
                id=self._id(ObservationId, "observation"),
                dependent_id=command.dependent_id, category=category,
                value_text=value, provenance=provenance,
            ) for category, value in command.observations)
            checkin = DailyCheckIn(
                id=self._id(CheckInId, "checkin"), dependent_id=command.dependent_id,
                note_text=command.note_text, observations=observations,
                provenance=provenance,
            )
            evaluation = self._policy.evaluate(command.signals)
            decision = SafetyDecision(
                id=self._id(SafetyDecisionId, "safety"),
                dependent_id=command.dependent_id, evaluation=evaluation,
                provenance=provenance,
            )
            uow.repo.add_checkin(checkin)
            for observation in observations:
                uow.repo.add_observation(observation)
            uow.repo.add_safety_decision(decision)
            self._audit(
                uow.repo, action=AuditAction.CHECKIN_RECORDED,
                caregiver_id=caregiver_id, subject_ref=str(checkin.id),
                provenance=provenance,
            )
            self._audit(
                uow.repo, action=AuditAction.SAFETY_EVALUATED,
                caregiver_id=caregiver_id, subject_ref=str(decision.id),
                provenance=provenance,
                detail=(("disposition", evaluation.disposition.value),
                        ("policy_version", evaluation.policy_version)),
            )
            self._remember(uow.repo, command.provider_event_id, "checkin", str(checkin.id))
            uow.commit()
            return CheckInResult(checkin.id, decision.id, evaluation)

    def build_clinician_report(self, command: BuildClinicianReport) -> ClinicianReport:
        with self._uow_factory() as uow:
            dependent, _ = self._dependent_and_owner(uow.repo, command.dependent_id)
            timeline = uow.repo.timeline_for_dependent(dependent.id)
            provenance = self._provenance(
                Actor(ActorKind.SYSTEM, "lumi"), ConfirmationState.CONFIRMED
            )
            return build_clinician_report(
                report_id=self._id(ReportId, "report"), dependent_id=dependent.id,
                plan=uow.repo.get_plan_for_dependent(dependent.id),
                mentions=timeline.mentions, observations=timeline.observations,
                media=timeline.media, candidate_patterns=(),
                policy_version=self._policy.version, generated_at=self._clock.now(),
                provenance=provenance,
            )

    def export_caregiver_data(self, command: ExportCaregiverData) -> CaregiverExport:
        with self._uow_factory() as uow:
            return uow.repo.export_caregiver(command.caregiver_id)

    def delete_caregiver_data(self, command: DeleteCaregiverData) -> DeletionReceipt:
        with self._uow_factory() as uow:
            if command.actor.kind is not ActorKind.CAREGIVER or command.actor.ref != str(
                command.caregiver_id
            ):
                raise OwnershipError("only the owning caregiver may delete the account")
            receipt = uow.repo.delete_caregiver(command.caregiver_id)
            uow.commit()
            return receipt
