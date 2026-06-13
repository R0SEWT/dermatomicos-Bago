"""Safety policy port.

The only input is structured ``ObservationSignals`` and the only output is a
``SafetyEvaluation``. There is no field through which a model could pass a
desired disposition, suppress a rule, or inject caregiver-facing copy.
"""

from __future__ import annotations

from typing import Protocol

from ..domain.safety_decision import SafetyEvaluation
from ..domain.signals import ObservationSignals


class SafetyPolicy(Protocol):
    @property
    def version(self) -> str: ...

    def evaluate(self, signals: ObservationSignals) -> SafetyEvaluation: ...
