"""Id generator port. Ids are injected so aggregates stay pure."""

from __future__ import annotations

from typing import Protocol


class IdGenerator(Protocol):
    def new(self, prefix: str) -> str:
        """Return a fresh opaque id, optionally namespaced by ``prefix``."""
        ...
