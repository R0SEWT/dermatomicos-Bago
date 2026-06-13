from datetime import datetime, timezone

from lumi.application.ai_mapping import map_ai_plan_proposal
from lumi.domain.enums import ActorKind, TreatmentSource
from lumi.domain.provenance import Actor
from lumi.ports.ai import AIPlanProposal, ProposedPlanItem, VersionStamp


def test_ambiguous_ai_items_never_enter_domain_proposal():
    version = VersionStamp("gpt-4.1", "2025-04-14", "v1", "s1", "p1", "e1")
    ai_proposal = AIPlanProposal((
        ProposedPlanItem("crema medica", TreatmentSource.PRESCRIBED, "crema", 0.9, False),
        ProposedPlanItem("otra crema", None, "otra crema", 0.5, True),
    ), version)
    mapped = map_ai_plan_proposal(
        ai_proposal, dependent_id="dep", model_actor=Actor(ActorKind.MODEL, "gpt-4.1"),
        recorded_at=datetime(2026, 6, 13, tzinfo=timezone.utc),
        source_message_id="message", provider_event_id="event",
    )
    assert len(mapped.proposal.items) == 1
    assert mapped.proposal.items[0].source is TreatmentSource.PRESCRIBED
    assert mapped.follow_up_items == ("otra crema",)
    assert mapped.non_prescribed_items == ()


def test_non_prescribed_ai_items_are_routed_outside_plan():
    version = VersionStamp("gpt-4.1", "2025-04-14", "v1", "s1", "p1", "e1")
    ai_proposal = AIPlanProposal((
        ProposedPlanItem(
            "manzanilla", TreatmentSource.NON_PRESCRIBED,
            "manzanilla", 0.9, False,
        ),
    ), version)

    mapped = map_ai_plan_proposal(
        ai_proposal, dependent_id="dep", model_actor=Actor(ActorKind.MODEL, "gpt-4.1"),
        recorded_at=datetime(2026, 6, 13, tzinfo=timezone.utc),
        source_message_id="message", provider_event_id="event",
    )

    assert mapped.proposal is None
    assert mapped.follow_up_items == ()
    assert mapped.non_prescribed_items == ("manzanilla",)
