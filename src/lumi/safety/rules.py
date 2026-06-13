"""Rule-set representation as data, not code branches.

Rules and caregiver-facing copy are clinician-ownable data so they can be
reviewed and versioned without changing evaluation logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.enums import SafetyDisposition


@dataclass(frozen=True)
class Condition:
    signal: str
    op: str  # ">=" ">" "<=" "<" "==" "is_true"
    value: float | int | bool = True


@dataclass(frozen=True)
class RedFlagRule:
    id: str
    all_of: tuple[Condition, ...]
    disposition: SafetyDisposition
    approved_copy_key: str
    rationale: str


@dataclass(frozen=True)
class RuleSet:
    version: str
    rules: tuple[RedFlagRule, ...]
    approved_copy: tuple[tuple[str, str], ...]
    default_disposition: SafetyDisposition = SafetyDisposition.CONTINUE_RECORDING
    default_copy_key: str = "continue"

    def copy_for(self, key: str) -> str:
        for k, text in self.approved_copy:
            if k == key:
                return text
        raise KeyError(f"no approved copy for key {key!r}")
