"""Clock port. Time is injected so the domain stays deterministic and testable."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current tz-aware UTC time."""
        ...
