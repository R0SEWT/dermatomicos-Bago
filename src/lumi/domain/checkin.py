"""Daily check-in and its individual observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .ids import CheckInId, DependentId, ObservationId
from .provenance import Provenance


@dataclass(frozen=True)
class Observation:
    """One structured fact extracted/recorded from a check-in.

    ``effective_date`` is the day the fact is *about*, resolved from a relative
    expression in the note ("anteayer le di la crema"). It defaults to ``None``,
    in which case consumers fall back to ``provenance.recorded_at`` — the
    message date. It never overrides provenance, which stays the audit record.
    """

    id: ObservationId
    dependent_id: DependentId
    category: str
    value_text: str
    provenance: Provenance
    effective_date: date | None = None


@dataclass(frozen=True)
class DailyCheckIn:
    """A single nightly interaction; the raw note plus its observations."""

    id: CheckInId
    dependent_id: DependentId
    note_text: str
    observations: tuple[Observation, ...]
    provenance: Provenance
