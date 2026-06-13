"""Default runtime implementations of the clock and id-generator ports."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


class SystemClock:
    """Real wall-clock in tz-aware UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class UuidGenerator:
    """Opaque ids namespaced by a short prefix."""

    def new(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
