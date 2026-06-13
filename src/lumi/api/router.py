"""Deterministic command router for the local conversation adapter."""

from __future__ import annotations

from dataclasses import dataclass

from ..adapters.reports.markdown import render_clinician_report
from ..application.ai_mapping import map_ai_plan_proposal
from ..application.commands import (
    BuildClinicianReport, ConfirmMedicalPlanVersion, DeleteCaregiverData,
    ExportCaregiverData, ProposeMedicalPlan, RecordCheckIn, RegisterCaregiver,
    RegisterDependent,
)
from ..application.service import LumiApplication
from ..domain.enums import ActorKind, ConfirmationState, TreatmentSource
from ..domain.ids import CaregiverId, DependentId, ProposalRef, ProviderEventId
from ..domain.plan import PlanProposal, ProposedPlanItem
from ..domain.provenance import Actor, ExternalIdentity, Provenance
from ..domain.signals import ObservationSignals
from ..ports.ai import AIExtractionPort, ExtractionContext
from ..ports.channel import InboundMessage

HELP = (
    "Comandos: /start <alias> [mes-nacimiento], /plan <item>|<item>, /plan-ai <texto>, "
    "/confirm [indices], /checkin <texto; clave=valor>, /report, /export, /delete"
)


@dataclass
class ConversationSession:
    identity: ExternalIdentity
    caregiver_id: CaregiverId | None = None
    dependent_id: DependentId | None = None
    proposal_ref: ProposalRef | None = None


class ConversationRouter:
    def __init__(
        self, application: LumiApplication, ai: AIExtractionPort | None = None
    ) -> None:
        self._app = application
        self._ai = ai

    @staticmethod
    def _event(message: InboundMessage, suffix: str) -> ProviderEventId:
        return ProviderEventId(f"{message.provider_event_id}:{suffix}")

    @staticmethod
    def _require_profile(session: ConversationSession) -> tuple[CaregiverId, DependentId]:
        if session.caregiver_id is None or session.dependent_id is None:
            raise ValueError("Primero usa /start <alias>.")
        return session.caregiver_id, session.dependent_id

    def route(self, message: InboundMessage, session: ConversationSession) -> str:
        text = message.text.strip()
        command, _, argument = text.partition(" ")
        command = command.lower()
        if command in {"/help", "help"}:
            return HELP
        if command == "/start":
            parts = argument.split()
            if not parts:
                raise ValueError("Uso: /start <alias> [AAAA-MM]")
            caregiver_id = self._app.register_caregiver(RegisterCaregiver(
                message.identity, provider_event_id=self._event(message, "caregiver")
            ))
            dependent_id = self._app.register_dependent(RegisterDependent(
                caregiver_id=caregiver_id, alias=parts[0],
                birth_month=parts[1] if len(parts) > 1 else None,
                provider_event_id=self._event(message, "dependent"),
            ))
            session.caregiver_id = caregiver_id
            session.dependent_id = dependent_id
            return f"Perfil creado para {parts[0]}."
        caregiver_id, dependent_id = self._require_profile(session)
        if command == "/plan-ai":
            if self._ai is None:
                raise ValueError("La extraccion IA no esta configurada.")
            extracted = self._ai.extract_plan_proposal(
                argument, ExtractionContext(correlation_id=str(message.provider_event_id))
            )
            mapped = map_ai_plan_proposal(
                extracted, dependent_id=dependent_id,
                model_actor=Actor(ActorKind.MODEL, extracted.version.deployment),
                recorded_at=message.received_at,
                source_message_id=str(message.provider_event_id),
                provider_event_id=message.provider_event_id,
            )
            if mapped.proposal is None:
                return "Necesito confirmar la fuente de: " + "; ".join(mapped.follow_up_items)
            session.proposal_ref = self._app.propose_medical_plan(ProposeMedicalPlan(
                mapped.proposal, self._event(message, "ai-proposal")
            ))
            suffix = (
                " Fuente por confirmar: " + "; ".join(mapped.follow_up_items)
                if mapped.follow_up_items else ""
            )
            return f"Propuesta IA guardada. Usa /confirm.{suffix}"
        if command == "/plan":
            raw_items = tuple(part.strip() for part in argument.split("|") if part.strip())
            if not raw_items:
                raise ValueError("Uso: /plan <indicacion>|<indicacion>")
            items = tuple(self._parse_plan_item(item) for item in raw_items)
            provenance = Provenance(
                actor=Actor(ActorKind.CAREGIVER, str(caregiver_id)),
                recorded_at=message.received_at,
                confirmation_state=ConfirmationState.PROPOSED,
                source_message_id=str(message.provider_event_id),
                provider_event_id=message.provider_event_id,
            )
            session.proposal_ref = self._app.propose_medical_plan(ProposeMedicalPlan(
                PlanProposal(dependent_id, items, provenance),
                self._event(message, "proposal"),
            ))
            prescribed = sum(item.source is TreatmentSource.PRESCRIBED for item in items)
            return f"Plan propuesto con {prescribed} items prescritos. Usa /confirm."
        if command == "/confirm":
            if session.proposal_ref is None:
                raise ValueError("No hay una propuesta pendiente.")
            indexes = tuple(int(value) - 1 for value in argument.split()) if argument else (0,)
            version_id = self._app.confirm_medical_plan(ConfirmMedicalPlanVersion(
                dependent_id, session.proposal_ref, indexes,
                Actor(ActorKind.CAREGIVER, str(caregiver_id)),
                self._event(message, "confirm"),
            ))
            return f"Plan confirmado: {version_id}."
        if command == "/checkin":
            note, observations, signals = self._parse_checkin(argument)
            result = self._app.record_checkin(RecordCheckIn(
                dependent_id, note, observations, signals,
                source_message_id=str(message.provider_event_id),
                provider_event_id=self._event(message, "checkin"),
            ))
            return " ".join(result.safety.messages)
        if command == "/report":
            report = self._app.build_clinician_report(BuildClinicianReport(dependent_id))
            return render_clinician_report(report)
        if command == "/export":
            exported = self._app.export_caregiver_data(ExportCaregiverData(caregiver_id))
            return (
                f"Export: {len(exported.dependents)} dependientes, "
                f"{len(exported.plans)} planes, {len(exported.checkins)} check-ins."
            )
        if command == "/delete":
            receipt = self._app.delete_caregiver_data(DeleteCaregiverData(
                caregiver_id, Actor(ActorKind.CAREGIVER, str(caregiver_id)),
                self._event(message, "delete"),
            ))
            session.caregiver_id = None
            session.dependent_id = None
            session.proposal_ref = None
            return f"Datos eliminados: {receipt.total} registros."
        raise ValueError(HELP)

    @staticmethod
    def _parse_plan_item(text: str) -> ProposedPlanItem:
        lowered = text.lower()
        if lowered.startswith("np:") or lowered.startswith("no_prescrito:"):
            _, _, instruction = text.partition(":")
            return ProposedPlanItem(TreatmentSource.NON_PRESCRIBED, instruction.strip())
        return ProposedPlanItem(TreatmentSource.PRESCRIBED, text)

    @staticmethod
    def _parse_checkin(
        text: str,
    ) -> tuple[str, tuple[tuple[str, str], ...], ObservationSignals]:
        parts = tuple(part.strip() for part in text.split(";") if part.strip())
        note_parts: list[str] = []
        observations: list[tuple[str, str]] = []
        values: dict[str, object] = {}
        bool_keys = {
            "letargo": "lethargy", "come_poco": "poor_feeding",
            "rash_extendido": "spreading_rash", "pus_ampollas": "rash_with_pus_or_blisters",
            "respiracion": "breathing_difficulty", "llanto_inconsolable": "inconsolable_crying",
        }
        for part in parts:
            key, separator, value = part.partition("=")
            if not separator:
                note_parts.append(part)
            elif key in {"fiebre", "edad_meses"}:
                values["fever_c" if key == "fiebre" else "age_months"] = (
                    float(value) if key == "fiebre" else int(value)
                )
            elif key in bool_keys:
                values[bool_keys[key]] = value.lower() in {"si", "true", "1"}
            else:
                observations.append((key, value))
        note = "; ".join(note_parts) or text
        return note, tuple(observations), ObservationSignals(**values)
