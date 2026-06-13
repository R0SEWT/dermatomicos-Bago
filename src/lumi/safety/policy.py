"""Versioned red-flag policy evaluator (pure function over signals + rule set)."""

from __future__ import annotations

from ..domain.enums import DISPOSITION_RANK, SafetyDisposition
from ..domain.safety_decision import SafetyEvaluation
from ..domain.signals import ObservationSignals
from .rules import Condition, RuleSet


def _eval_condition(cond: Condition, signals: ObservationSignals) -> bool:
    actual = getattr(signals, cond.signal, None)
    if cond.op == "is_true":
        return actual is True
    if actual is None:
        return False
    if cond.op == ">=":
        return actual >= cond.value
    if cond.op == ">":
        return actual > cond.value
    if cond.op == "<=":
        return actual <= cond.value
    if cond.op == "<":
        return actual < cond.value
    if cond.op == "==":
        return actual == cond.value
    raise ValueError(f"unknown operator {cond.op!r}")


class VersionedRedFlagPolicy:
    """Implements ``ports.policy.SafetyPolicy`` over a fixed rule set."""

    def __init__(self, ruleset: RuleSet) -> None:
        self._ruleset = ruleset

    @property
    def version(self) -> str:
        return self._ruleset.version

    def evaluate(self, signals: ObservationSignals) -> SafetyEvaluation:
        matched = [
            rule
            for rule in self._ruleset.rules
            if all(_eval_condition(c, signals) for c in rule.all_of)
        ]
        if not matched:
            return SafetyEvaluation(
                disposition=self._ruleset.default_disposition,
                matched_rule_ids=(),
                messages=(self._ruleset.copy_for(self._ruleset.default_copy_key),),
                policy_version=self._ruleset.version,
            )

        disposition = max(matched, key=lambda r: DISPOSITION_RANK[r.disposition]).disposition
        # deterministic, order-independent message set for matched rules
        messages = tuple(
            self._ruleset.copy_for(rule.approved_copy_key) for rule in matched
        )
        return SafetyEvaluation(
            disposition=disposition,
            matched_rule_ids=tuple(rule.id for rule in matched),
            messages=messages,
            policy_version=self._ruleset.version,
        )


__all__ = ["VersionedRedFlagPolicy", "SafetyDisposition"]
