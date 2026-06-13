"""Outputs of the deterministic safety policy.

``SafetyEvaluation`` is the pure result a policy returns given signals (no id,
no provenance). ``SafetyDecision`` is the persisted fact the application builds
by wrapping an evaluation with id + provenance.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import SafetyDisposition
from .ids import DependentId, SafetyDecisionId
from .provenance import Provenance


@dataclass(frozen=True)
class SafetyEvaluation:
    """Pure result of evaluating signals against a versioned rule set."""

    disposition: SafetyDisposition
    matched_rule_ids: tuple[str, ...]
    messages: tuple[str, ...]
    policy_version: str


@dataclass(frozen=True)
class SafetyDecision:
    """The persisted record of a safety evaluation."""

    id: SafetyDecisionId
    dependent_id: DependentId
    evaluation: SafetyEvaluation
    provenance: Provenance
