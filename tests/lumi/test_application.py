from dataclasses import replace
from datetime import date

import pytest

from lumi.adapters.persistence.in_memory import InMemoryRepository, InMemoryUnitOfWork
from lumi.application.commands import (
    BuildClinicianReport, ConfirmMedicalPlanVersion, DeleteCaregiverData,
    ExportCaregiverData, ProposeMedicalPlan, RecordCheckIn, RecordTreatmentMention,
    RegisterCaregiver, RegisterDependent,
)
from lumi.domain.enums import ActorKind, ConfirmationState, SafetyDisposition, TreatmentSource
from lumi.domain.errors import IdempotencyViolation, ProposalCannotActivateError
from lumi.domain.plan import PlanProposal, ProposedPlanItem
from lumi.domain.provenance import Actor, ExternalIdentity, Provenance
from lumi.domain.signals import ObservationSignals
from lumi.safety.policy import VersionedRedFlagPolicy
from lumi.safety.rulesets.v1 import RULESET_V1


def _onboard(app):
    caregiver = app.register_caregiver(RegisterCaregiver(
        ExternalIdentity("console", "bsuid-123"),
        provider_event_id="event-caregiver",
    ))
    dependent = app.register_dependent(RegisterDependent(
        caregiver, "bebe", "2025-01", "event-dependent"
    ))
    return caregiver, dependent


def _proposal(app, dependent, actor_kind=ActorKind.CAREGIVER):
    provenance = Provenance(
        Actor(actor_kind, "extractor"), None, ConfirmationState.PROPOSED,
        source_message_id="message-plan",
    )
    proposal = PlanProposal(dependent, (
        ProposedPlanItem(TreatmentSource.PRESCRIBED, "Aplicar crema indicada"),
        ProposedPlanItem(TreatmentSource.NON_PRESCRIBED, "manzanilla"),
    ), provenance)
    return app.propose_medical_plan(ProposeMedicalPlan(proposal, "event-proposal"))


def test_proposal_cannot_activate_without_caregiver_actor(app, store):
    caregiver, dependent = _onboard(app)
    proposal_ref = _proposal(app, dependent, ActorKind.MODEL)
    with pytest.raises(ProposalCannotActivateError):
        app.confirm_medical_plan(ConfirmMedicalPlanVersion(
            dependent, proposal_ref, (0,), Actor(ActorKind.MODEL, "gpt-4.1"),
            "event-confirm",
        ))
    assert store.plans == {}


def test_plan_confirmation_is_versioned_and_idempotent(app, store):
    caregiver, dependent = _onboard(app)
    proposal_ref = _proposal(app, dependent)
    command = ConfirmMedicalPlanVersion(
        dependent, proposal_ref, (0,), Actor(ActorKind.CAREGIVER, str(caregiver)),
        "event-confirm",
    )
    first = app.confirm_medical_plan(command)
    second = app.confirm_medical_plan(command)
    assert first == second
    plan = InMemoryRepository(store).get_plan_for_dependent(dependent)
    assert len(plan.versions) == 1
    assert plan.active_version.items[0].source is TreatmentSource.PRESCRIBED


def test_provider_event_cannot_be_reused_for_another_command(app):
    caregiver = app.register_caregiver(RegisterCaregiver(
        ExternalIdentity("console", "id"), provider_event_id="same-event"
    ))
    with pytest.raises(IdempotencyViolation):
        app.register_dependent(RegisterDependent(
            caregiver, "bebe", provider_event_id="same-event"
        ))


def test_checkin_uses_highest_deterministic_disposition(app, store):
    _, dependent = _onboard(app)
    result = app.record_checkin(RecordCheckIn(
        dependent, "Tiene fiebre y dificultad para respirar",
        observations=(("sleep", "durmio poco"),),
        signals=ObservationSignals(fever_c=39.2, breathing_difficulty=True),
        provider_event_id="event-checkin",
    ))
    replay = app.record_checkin(RecordCheckIn(
        dependent, "ignored on replay", provider_event_id="event-checkin"
    ))
    assert result == replay
    assert result.safety.disposition is SafetyDisposition.URGENT_CARE
    assert set(result.safety.matched_rule_ids) == {"breathing", "high_fever"}
    assert len(store.checkins) == 1


def test_safety_policy_output_is_order_independent_and_deduplicated():
    signals = ObservationSignals(breathing_difficulty=True, lethargy=True)
    forward = VersionedRedFlagPolicy(RULESET_V1).evaluate(signals)
    reversed_rules = replace(RULESET_V1, rules=tuple(reversed(RULESET_V1.rules)))
    backward = VersionedRedFlagPolicy(reversed_rules).evaluate(signals)

    assert forward == backward
    assert forward.matched_rule_ids == ("breathing", "lethargy")
    assert len(forward.messages) == 1


def test_end_to_end_report_export_and_delete(app, store):
    caregiver, dependent = _onboard(app)
    proposal_ref = _proposal(app, dependent)
    app.confirm_medical_plan(ConfirmMedicalPlanVersion(
        dependent, proposal_ref, (0,), Actor(ActorKind.CAREGIVER, str(caregiver)),
        "event-confirm",
    ))
    plan = InMemoryRepository(store).get_plan_for_dependent(dependent)
    item_id = plan.active_version.items[0].id
    app.record_treatment_mention(RecordTreatmentMention(
        dependent, TreatmentSource.PRESCRIBED, "crema aplicada", item_id,
        provider_event_id="event-prescribed",
    ))
    app.record_treatment_mention(RecordTreatmentMention(
        dependent, TreatmentSource.NON_PRESCRIBED, "manzanilla",
        provider_event_id="event-remedy",
    ))
    app.record_checkin(RecordCheckIn(
        dependent, "Durmio mejor", observations=(("sleep", "mejor"),),
        provider_event_id="event-checkin",
    ))
    report = app.build_clinician_report(BuildClinicianReport(dependent))
    assert report.plan_version_id == plan.active_version.id
    assert report.plan_version_number == 1
    assert report.policy_version == "redflag-v1"
    assert report.adherence[0].observed_count == 1
    assert [line.text for line in report.non_prescribed_items] == ["manzanilla"]
    assert app.export_caregiver_data(ExportCaregiverData(caregiver)).checkins
    receipt = app.delete_caregiver_data(DeleteCaregiverData(
        caregiver, Actor(ActorKind.CAREGIVER, str(caregiver)), "event-delete"
    ))
    assert receipt.total > 0
    assert store.caregivers == {}
    assert store.dependents == {}
    assert store.plans == {}
    assert store.checkins == []
    assert store.proposals == {}
    assert store.event_results == {}
    assert store.mentions == []
    assert store.observations == []
    assert store.safety_decisions == []


# The suite's FixedClock is anchored to 2026-06-13; relative expressions in a
# check-in/mention note must date the fact to the event day, not the message day.
def test_checkin_dates_observations_from_relative_expression(app, store):
    _, dependent = _onboard(app)
    app.record_checkin(RecordCheckIn(
        dependent, "Anteayer le cambiamos a un jabón nuevo",
        observations=(("exposure", "jabón nuevo"),),
        provider_event_id="event-checkin",
    ))
    assert store.observations[0].effective_date == date(2026, 6, 11)


def test_report_evolution_uses_relative_event_date(app):
    _, dependent = _onboard(app)
    app.record_checkin(RecordCheckIn(
        dependent, "Anteayer se rasco bastante",
        observations=(("scratching", "bastante"),),
        provider_event_id="event-checkin",
    ))

    report = app.build_clinician_report(BuildClinicianReport(dependent))

    assert report.symptom_sleep_evolution[0].on == date(2026, 6, 11)


def test_checkin_without_relative_expression_leaves_effective_date_none(app, store):
    _, dependent = _onboard(app)
    app.record_checkin(RecordCheckIn(
        dependent, "Durmió tranquila anoche",  # 'anoche' is not a day shift
        observations=(("sleep", "bien"),),
        provider_event_id="event-checkin",
    ))
    obs = store.observations[0]
    assert obs.effective_date is None
    # Falls back to the message date, so provenance stays the audit record.
    assert obs.provenance.recorded_at.date() == date(2026, 6, 13)


def test_treatment_mention_dates_from_relative_expression(app, store):
    _, dependent = _onboard(app)
    app.record_treatment_mention(RecordTreatmentMention(
        dependent, TreatmentSource.NON_PRESCRIBED,
        "Hace 3 días le puse manzanilla",
        provider_event_id="event-remedy",
    ))
    assert store.mentions[0].effective_date == date(2026, 6, 10)


def test_unit_of_work_rolls_back_uncommitted_changes(store):
    with InMemoryUnitOfWork(store) as uow:
        uow.repo.remember_provider_event("event", "thing:id")
    assert store.event_results == {}
