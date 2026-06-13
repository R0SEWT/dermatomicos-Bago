"""Structured, typed signals consumed by the deterministic safety policy.

These are bounded, typed fields — never free text and never model prose. The
language model (later phase) may only populate these fields; it can never emit
a disposition. This is the seam that makes red-flag escalation deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObservationSignals:
    age_months: int | None = None
    fever_c: float | None = None
    lethargy: bool = False
    poor_feeding: bool = False
    spreading_rash: bool = False
    rash_with_pus_or_blisters: bool = False
    breathing_difficulty: bool = False
    inconsolable_crying: bool = False
