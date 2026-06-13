from datetime import datetime, timezone

import pytest

from lumi.adapters.persistence.in_memory import InMemoryStore, InMemoryUnitOfWork
from lumi.application.service import LumiApplication
from lumi.safety.policy import VersionedRedFlagPolicy
from lumi.safety.rulesets.v1 import RULESET_V1


class FixedClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value


class SeqIdGenerator:
    def __init__(self) -> None:
        self.value = 0

    def new(self, prefix: str) -> str:
        self.value += 1
        return f"{prefix}-{self.value}"


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def app(store):
    return LumiApplication(
        lambda: InMemoryUnitOfWork(store),
        FixedClock(),
        SeqIdGenerator(),
        VersionedRedFlagPolicy(RULESET_V1),
    )
