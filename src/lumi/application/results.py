"""Application result objects for multi-record use cases."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.ids import CheckInId, SafetyDecisionId
from ..domain.safety_decision import SafetyEvaluation


@dataclass(frozen=True)
class CheckInResult:
    checkin_id: CheckInId
    safety_decision_id: SafetyDecisionId
    safety: SafetyEvaluation
