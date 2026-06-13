"""Treatment mentions recorded from caregiver messages.

A ``TreatmentMention`` has no schedule attribute at all, so there is nothing on
a non-prescribed mention from which a reminder could ever be derived. Reminders
(future phases) are derivable only from a confirmed ``PlanItem.adherence_schedule``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .enums import TreatmentSource
from .errors import NonPrescribedLinkError
from .ids import DependentId, MentionId, PlanItemId
from .provenance import Provenance


@dataclass(frozen=True)
class TreatmentMention:
    """A neutrally-recorded treatment the caregiver mentioned.

    ``effective_date`` is the day the mention is *about*, resolved from a
    relative expression in the message ("hace 3 días le puse manzanilla"). It
    defaults to ``None`` (consumers fall back to ``provenance.recorded_at``) and
    never overrides provenance, which stays the audit record.
    """

    id: MentionId
    dependent_id: DependentId
    source: TreatmentSource
    text: str
    provenance: Provenance
    linked_plan_item_id: PlanItemId | None = None
    effective_date: date | None = None

    def __post_init__(self) -> None:
        if (
            self.source is TreatmentSource.NON_PRESCRIBED
            and self.linked_plan_item_id is not None
        ):
            raise NonPrescribedLinkError(
                "a non_prescribed mention cannot link to a plan item"
            )
