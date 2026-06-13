"""Caregiver account and dependent child profile."""

from __future__ import annotations

from dataclasses import dataclass

from .ids import CaregiverId, DependentId
from .provenance import ExternalIdentity, Provenance


@dataclass(frozen=True)
class CaregiverAccount:
    """The account holder and owner of all submitted data.

    Identity is a set of opaque ``(channel, opaque_id)`` pairs. There is
    deliberately no phone-number field anywhere in the domain.
    """

    id: CaregiverId
    identities: tuple[ExternalIdentity, ...]
    locale: str
    provenance: Provenance

    def has_identity(self, channel: str, opaque_id: str) -> bool:
        return any(i.channel == channel and i.opaque_id == opaque_id for i in self.identities)


@dataclass(frozen=True)
class DependentProfile:
    """A dependent child profile, owned by exactly one caregiver.

    ``alias`` is not the child's real name and ``birth_month`` is a coarse band,
    never a full date of birth (privacy by design).
    """

    id: DependentId
    caregiver_id: CaregiverId
    alias: str
    birth_month: str | None
    provenance: Provenance
