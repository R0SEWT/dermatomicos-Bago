"""Translate untrusted AI DTOs into inert domain proposals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain.enums import ConfirmationState
from ..domain.ids import DependentId, ProviderEventId
from ..domain.plan import PlanProposal, ProposedPlanItem as DomainProposedPlanItem
from ..domain.provenance import Actor, Provenance
from ..ports.ai import AIPlanProposal


@dataclass(frozen=True)
class PlanMappingResult:
    proposal: PlanProposal | None
    follow_up_items: tuple[str, ...]


def map_ai_plan_proposal(
    proposal: AIPlanProposal,
    *,
    dependent_id: DependentId,
    model_actor: Actor,
    recorded_at: datetime,
    source_message_id: str,
    provider_event_id: ProviderEventId,
) -> PlanMappingResult:
    """Exclude ambiguous items; no AI DTO can activate or confirm a plan."""
    clear = tuple(
        DomainProposedPlanItem(
            source=item.source,
            instruction_text=item.description,
            schedule_hint=item.cadence_hint,
        )
        for item in proposal.items
        if not item.ambiguous_source and item.source is not None
    )
    follow_up = tuple(
        item.description
        for item in proposal.items
        if item.ambiguous_source or item.source is None
    )
    if not clear:
        return PlanMappingResult(None, follow_up)
    provenance = Provenance(
        actor=model_actor,
        recorded_at=recorded_at,
        confirmation_state=ConfirmationState.PROPOSED,
        source_message_id=source_message_id,
        provider_event_id=provider_event_id,
    )
    return PlanMappingResult(PlanProposal(dependent_id, clear, provenance), follow_up)
