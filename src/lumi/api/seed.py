"""Scripted multi-night demo scenario.

Loads a realistic six-night history into the in-memory store so the demo looks
complete on first load: a confirmed plan, an adherence trail, a non-prescribed
home remedy, a deterministic safety event, and a repeated coincidence that the
pattern detector surfaces ("el rascado nocturno se repitio despues de jabon
nuevo"). It also returns a cosmetic chat transcript telling that story; live
messages continue on top of it.

All data is written through the application service (the same path as live
messages), advancing :class:`DemoClock` day by day so observations land on
distinct calendar dates — the detector keys on the day.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..application.commands import (
    BuildClinicianReport, ConfirmMedicalPlanVersion, ExportCaregiverData,
    ProposeMedicalPlan, RecordCheckIn, RecordTreatmentMention, RegisterCaregiver,
    RegisterDependent,
)
from ..domain.enums import ActorKind, ConfirmationState, TreatmentSource
from ..domain.ids import CaregiverId, DependentId, PlanItemId
from ..domain.patterns import PatternTemplate
from ..domain.plan import PlanProposal, ProposedPlanItem
from ..domain.provenance import Actor, Provenance
from ..domain.signals import ObservationSignals
from .bootstrap import DemoRuntime

# Approved neutral copy for a recorded item outside the confirmed plan (PRODUCT.md).
_NON_PRESCRIBED_REPLY = (
    "Lo anoté. Como no forma parte del plan confirmado por tu pediatra, lo "
    "incluiré en el reporte para que puedan conversarlo en consulta."
)


@dataclass(frozen=True)
class ChatTurn:
    role: str  # "caregiver" | "lumi"
    text: str


@dataclass
class SeedResult:
    caregiver_id: CaregiverId
    dependent_id: DependentId
    transcript: tuple[ChatTurn, ...]


def seed_demo(runtime: DemoRuntime) -> SeedResult:
    """Populate the runtime's store + session with the demo scenario."""
    app = runtime.application
    clock = runtime.clock
    identity = runtime.session.identity
    today = clock.now()

    counter = {"n": 0}

    def event(tag: str) -> str:
        counter["n"] += 1
        return f"seed-{counter['n']:02d}-{tag}"

    def night(days_ago: int) -> datetime:
        moment = today - timedelta(days=days_ago)
        return moment.replace(hour=21, minute=0, second=0, microsecond=0)

    transcript: list[ChatTurn] = [
        ChatTurn("lumi", "Hola 👋 Soy Lumi. Te ayudo a seguir el plan de Sofía y "
                         "a anotar cómo evoluciona cada noche."),
    ]

    # --- Night -6: onboarding + confirmed plan + baseline check-in ---
    clock.set(night(6))
    caregiver_id = app.register_caregiver(RegisterCaregiver(
        identity, provider_event_id=event("caregiver")
    ))
    dependent_id = app.register_dependent(RegisterDependent(
        caregiver_id, "Sofía", "2025-02", provider_event_id=event("dependent")
    ))
    runtime.session.caregiver_id = caregiver_id
    runtime.session.dependent_id = dependent_id

    plan_provenance = Provenance(
        Actor(ActorKind.CAREGIVER, str(caregiver_id)), clock.now(),
        ConfirmationState.PROPOSED, source_message_id=event("plan-src"),
    )
    proposal_ref = app.propose_medical_plan(ProposeMedicalPlan(
        PlanProposal(dependent_id, (
            ProposedPlanItem(TreatmentSource.PRESCRIBED,
                             "Crema hidratante, aplicar 2 veces al día", "2 veces al día"),
            ProposedPlanItem(TreatmentSource.PRESCRIBED,
                             "Baño tibio diario con jabón suave", "diario"),
        ), plan_provenance),
        provider_event_id=event("proposal"),
    ))
    app.confirm_medical_plan(ConfirmMedicalPlanVersion(
        dependent_id, proposal_ref, (0, 1),
        Actor(ActorKind.CAREGIVER, str(caregiver_id)), provider_event_id=event("confirm"),
    ))
    export = app.export_caregiver_data(ExportCaregiverData(caregiver_id))
    crema_item_id: PlanItemId = export.plans[0].active_version.items[0].id

    transcript.append(ChatTurn(
        "caregiver", "El pediatra indicó crema hidratante 2 veces al día y baño tibio diario."
    ))
    transcript.append(ChatTurn(
        "lumi", "Registré el plan indicado por tu pediatra (v1): crema hidratante "
                "2 veces al día; baño tibio diario."
    ))

    def checkin(text: str, observations: tuple[tuple[str, str], ...] = (),
                signals: ObservationSignals | None = None, tag: str = "checkin") -> None:
        result = app.record_checkin(RecordCheckIn(
            dependent_id, text, observations, signals or ObservationSignals(),
            source_message_id=event(f"{tag}-src"), provider_event_id=event(tag),
        ))
        transcript.append(ChatTurn("caregiver", text))
        reply = " ".join(result.safety.messages).strip()
        if reply:
            transcript.append(ChatTurn("lumi", reply))

    def applied_cream(tag: str) -> None:
        app.record_treatment_mention(RecordTreatmentMention(
            dependent_id, TreatmentSource.PRESCRIBED, "Le apliqué la crema indicada",
            linked_plan_item_id=crema_item_id, provider_event_id=event(tag),
        ))

    checkin("Durmió tranquila anoche.", (("sleep", "durmió bien"),), tag="ci-baseline")
    applied_cream("mention-cream-1")

    # --- Night -5: exposure #1 ---
    clock.set(night(5))
    checkin("Le cambiamos a un jabón nuevo en el baño.",
            (("exposure", "jabón nuevo"),), tag="ci-exposure-1")
    applied_cream("mention-cream-2")

    # --- Night -4: discomfort #1 (one day after exposure #1) ---
    clock.set(night(4))
    checkin("Se rascó bastante y durmió mal.",
            (("scratching", "mucho rascado"), ("sleep", "mal")), tag="ci-symptom-1")

    # --- Night -3: safety event + non-prescribed remedy ---
    clock.set(night(3))
    checkin("La noté con algo de fiebre.", (("temperature", "39.2"),),
            ObservationSignals(age_months=16, fever_c=39.2), tag="ci-fever")
    app.record_treatment_mention(RecordTreatmentMention(
        dependent_id, TreatmentSource.NON_PRESCRIBED,
        "Le puse una crema de manzanilla que recomendó mi mamá",
        provider_event_id=event("mention-np"),
    ))
    transcript.append(ChatTurn(
        "caregiver", "Le puse una crema de manzanilla que recomendó mi mamá."
    ))
    transcript.append(ChatTurn("lumi", _NON_PRESCRIBED_REPLY))

    # --- Night -2: exposure #2 ---
    clock.set(night(2))
    checkin("Volvimos a usar el jabón nuevo en el baño.",
            (("exposure", "jabón nuevo"),), tag="ci-exposure-2")
    applied_cream("mention-cream-3")

    # --- Night -1: discomfort #2 (completes the repeated-after pattern) ---
    clock.set(night(1))
    checkin("Otra vez se rascó mucho y durmió interrumpido.",
            (("scratching", "mucho rascado"), ("sleep", "interrumpido")), tag="ci-symptom-2")

    # Surface the detected pattern as the closing Lumi turn. Mark *every* current
    # repeated-after pattern as already surfaced so a live check-in only announces
    # a genuinely new one. Copy is the approved template, never model prose.
    report = app.build_clinician_report(BuildClinicianReport(dependent_id))
    announced = False
    for pattern in report.candidate_patterns:
        if pattern.template is PatternTemplate.REPEATED_AFTER:
            runtime.session.surfaced_patterns.add(pattern.rendered)
            if not announced:
                transcript.append(ChatTurn(
                    "lumi",
                    f"Noté un patrón para validar: {pattern.rendered} "
                    "¿Quieres que lo marque para conversarlo con su pediatra?",
                ))
                announced = True

    # Return the clock to the present so live messages are dated today.
    clock.set(today)
    return SeedResult(caregiver_id, dependent_id, tuple(transcript))
