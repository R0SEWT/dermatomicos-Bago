"""Default runtime implementations of the clock and id-generator ports."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone


class SystemClock:
    """Real wall-clock in tz-aware UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class DemoClock:
    """A settable clock for the demo/seed.

    The seed advances ``now`` day by day so observations land on distinct dates
    (the pattern detector keys on the calendar day). After seeding, callers
    typically pin it to the present so live messages read as "today".
    """

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime.now(timezone.utc)

    def now(self) -> datetime:
        return self._now

    def set(self, value: datetime) -> None:
        self._now = value

    def advance(self, *, days: int = 0, hours: int = 0) -> None:
        self._now = self._now + timedelta(days=days, hours=hours)


class UuidGenerator:
    """Opaque ids namespaced by a short prefix."""

    def new(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
