"""Domain error hierarchy. No vendor exceptions leak into the domain."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain rule violations."""


class NonPrescribedCannotScheduleError(DomainError):
    """A non-prescribed treatment may never carry an adherence schedule."""


class NonPrescribedLinkError(DomainError):
    """A non-prescribed mention may not link to a confirmed plan item."""


class UnconfirmedItemInVersionError(DomainError):
    """A plan version may only contain confirmed items."""


class NonPrescribedInVersionError(DomainError):
    """Only prescribed items belong inside a medical plan version."""


class PlanVersionConflictError(DomainError):
    """A new plan version did not follow the active version monotonically."""


class CausalLanguageError(DomainError):
    """A candidate pattern attempted causal/diagnostic language."""


class ProposalCannotActivateError(DomainError):
    """Only a caregiver actor may confirm/activate a plan version."""


class OwnershipError(DomainError):
    """A profile or record does not belong to the acting caregiver."""


class NotFoundError(DomainError):
    """A referenced aggregate does not exist."""


class IdempotencyViolation(DomainError):
    """A provider event id was reused with a conflicting result."""
