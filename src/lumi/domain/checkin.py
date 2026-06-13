"""Daily check-in and its individual observations."""

from __future__ import annotations

from dataclasses import dataclass

from .ids import CheckInId, DependentId, ObservationId
from .provenance import Provenance


@dataclass(frozen=True)
class Observation:
    """One structured fact extracted/recorded from a check-in."""

    id: ObservationId
    dependent_id: DependentId
    category: str
    value_text: str
    provenance: Provenance


@dataclass(frozen=True)
class DailyCheckIn:
    """A single nightly interaction; the raw note plus its observations."""

    id: CheckInId
    dependent_id: DependentId
    note_text: str
    observations: tuple[Observation, ...]
    provenance: Provenance
