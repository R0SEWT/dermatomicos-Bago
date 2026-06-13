from dataclasses import FrozenInstanceError, fields

import pytest

from lumi.domain.audit import AuditEvent
from lumi.domain.checkin import DailyCheckIn, Observation
from lumi.domain.enums import ActorKind, ConfirmationState, TreatmentSource
from lumi.domain.errors import (
    CausalLanguageError,
    NonPrescribedCannotScheduleError,
    NonPrescribedInVersionError,
)
from lumi.domain.identity import CaregiverAccount, DependentProfile
from lumi.domain.media import MediaDocument
from lumi.domain.patterns import CandidatePattern, PatternTemplate
from lumi.domain.plan import (
    AdherenceSchedule,
    MedicalPlan,
    MedicalPlanVersion,
    PlanItem,
)
from lumi.domain.provenance import Actor, Provenance
from lumi.domain.report import ClinicianReport
from lumi.domain.safety_decision import SafetyDecision
from lumi.domain.treatment import TreatmentMention


def test_every_persisted_fact_requires_provenance():
    types = (
        AuditEvent, DailyCheckIn, Observation, CaregiverAccount, DependentProfile,
        MediaDocument, MedicalPlan, MedicalPlanVersion, PlanItem, ClinicianReport,
        SafetyDecision, TreatmentMention,
    )
    for record_type in types:
        field = next((item for item in fields(record_type) if item.name == "provenance"), None)
        assert field is not None, record_type.__name__
        assert field.default_factory.__class__.__name__ == "_MISSING_TYPE"


def test_non_prescribed_cannot_schedule_or_enter_version():
    provenance = Provenance(
        Actor(ActorKind.CAREGIVER, "cg"), None, ConfirmationState.CONFIRMED
    )
    with pytest.raises(NonPrescribedCannotScheduleError):
        PlanItem(
            "item", TreatmentSource.NON_PRESCRIBED, "remedio",
            ConfirmationState.CONFIRMED, provenance, AdherenceSchedule(1),
        )
    item = PlanItem(
        "item", TreatmentSource.NON_PRESCRIBED, "remedio",
        ConfirmationState.CONFIRMED, provenance,
    )
    with pytest.raises(NonPrescribedInVersionError):
        MedicalPlanVersion(
            "version", "plan", 1, (item,), Actor(ActorKind.CAREGIVER, "cg"),
            None, provenance,
        )
    assert not hasattr(TreatmentMention, "adherence_schedule")


def test_plan_versions_are_frozen_and_append_only():
    provenance = Provenance(
        Actor(ActorKind.CAREGIVER, "cg"), None, ConfirmationState.CONFIRMED
    )
    plan = MedicalPlan("plan", "dep", provenance)
    item = PlanItem(
        "item", TreatmentSource.PRESCRIBED, "crema",
        ConfirmationState.CONFIRMED, provenance,
    )
    version = MedicalPlanVersion(
        "v1", "plan", 1, (item,), Actor(ActorKind.CAREGIVER, "cg"), None,
        provenance,
    )
    activated = plan.with_new_version(version)
    assert plan.versions == ()
    assert activated.versions == (version,)
    with pytest.raises(FrozenInstanceError):
        version.version_number = 2
    with pytest.raises(AttributeError):
        activated.versions.append(version)


def test_patterns_use_approved_non_causal_language():
    provenance = Provenance(
        Actor(ActorKind.SYSTEM, "lumi"), None, ConfirmationState.PROPOSED
    )
    pattern = CandidatePattern.build(
        PatternTemplate.COINCIDES_WITH,
        {"symptom": "mas molestias", "exposure": "ropa de lana"},
        provenance,
    )
    assert pattern.status == "to_validate"
    with pytest.raises(CausalLanguageError):
        CandidatePattern.build(
            PatternTemplate.COINCIDES_WITH,
            {"symptom": "alergia", "exposure": "leche"},
            provenance,
        )
