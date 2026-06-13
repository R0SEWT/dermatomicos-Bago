"""Typed id aliases.

``NewType`` has zero runtime cost but makes signatures self-documenting and
stops a ``DependentId`` being passed where a ``PlanId`` is expected (caught by
static analysis / review). A report citing ``(PlanId, PlanVersionId)`` is then
unambiguous about which exact version it references.
"""

from __future__ import annotations

from typing import NewType

CaregiverId = NewType("CaregiverId", str)
DependentId = NewType("DependentId", str)
PlanId = NewType("PlanId", str)
PlanVersionId = NewType("PlanVersionId", str)
PlanItemId = NewType("PlanItemId", str)
ProposalRef = NewType("ProposalRef", str)
MentionId = NewType("MentionId", str)
CheckInId = NewType("CheckInId", str)
ObservationId = NewType("ObservationId", str)
MediaId = NewType("MediaId", str)
SafetyDecisionId = NewType("SafetyDecisionId", str)
ReportId = NewType("ReportId", str)
AuditId = NewType("AuditId", str)
ProviderEventId = NewType("ProviderEventId", str)
