"""Domain enumerations shared across aggregates."""

from __future__ import annotations

from enum import Enum


class TreatmentSource(Enum):
    """Where a treatment came from. Drives reminders and report sections."""

    PRESCRIBED = "prescribed"
    NON_PRESCRIBED = "non_prescribed"


class ConfirmationState(Enum):
    """Lifecycle of a model/caregiver proposal before it becomes authoritative."""

    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class SafetyDisposition(Enum):
    """Outcome of the deterministic red-flag policy, ordered by escalation."""

    CONTINUE_RECORDING = "continue_recording"
    CONTACT_CLINICIAN = "contact_clinician"
    URGENT_CARE = "urgent_care"


# Higher rank = more escalatory. Used to pick the max-severity matched rule.
DISPOSITION_RANK: dict[SafetyDisposition, int] = {
    SafetyDisposition.CONTINUE_RECORDING: 0,
    SafetyDisposition.CONTACT_CLINICIAN: 1,
    SafetyDisposition.URGENT_CARE: 2,
}


class ActorKind(Enum):
    """Who caused a state change. Only CAREGIVER may activate a plan version."""

    CAREGIVER = "caregiver"
    SYSTEM = "system"
    CLINICIAN = "clinician"
    MODEL = "model"


class AuditAction(Enum):
    """Auditable application actions."""

    ACCOUNT_CREATED = "account_created"
    DEPENDENT_CREATED = "dependent_created"
    PLAN_PROPOSED = "plan_proposed"
    PLAN_CONFIRMED = "plan_confirmed"
    PLAN_REJECTED = "plan_rejected"
    MENTION_RECORDED = "mention_recorded"
    CHECKIN_RECORDED = "checkin_recorded"
    SAFETY_EVALUATED = "safety_evaluated"
    REPORT_BUILT = "report_built"
    DATA_EXPORTED = "data_exported"
    DATA_DELETED = "data_deleted"
