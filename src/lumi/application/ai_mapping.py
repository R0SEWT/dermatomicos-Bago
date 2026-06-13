"""Translate untrusted AI DTOs into inert domain proposals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain.enums import ConfirmationState
from ..domain.ids import DependentId, ProviderEventId
from ..domain.plan import PlanProposal, ProposedPlanItem as DomainProposedPlanItem
from ..domain.provenance import Actor, Provenance
from ..domain.signals import ObservationSignals
from ..ports.ai import AIPlanProposal, ObservationProposal


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


def map_ai_observations(
    proposal: ObservationProposal,
) -> tuple[tuple[tuple[str, str], ...], ObservationSignals]:
    """Translate an untrusted observation proposal into check-in inputs.

    Returns ``(observations, signals)`` ready for ``RecordCheckIn``. The AI can
    only populate structured fields here; the deterministic safety policy still
    decides any disposition. Ambiguous-source observations are kept (they are
    neutral facts), they simply do not become treatment mentions.
    """
    observations = tuple(
        (obs.category, obs.value_text) for obs in proposal.observations
    )
    s = proposal.signals
    signals = ObservationSignals(
        age_months=s.age_months, fever_c=s.fever_c, lethargy=s.lethargy,
        poor_feeding=s.poor_feeding, spreading_rash=s.spreading_rash,
        rash_with_pus_or_blisters=s.rash_with_pus_or_blisters,
        breathing_difficulty=s.breathing_difficulty,
        inconsolable_crying=s.inconsolable_crying,
    )
    return observations, signals
