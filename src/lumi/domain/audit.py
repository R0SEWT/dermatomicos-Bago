"""Audit trail. Detail is redacted key/values, never message bodies."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import AuditAction
from .ids import AuditId, CaregiverId
from .provenance import Provenance


@dataclass(frozen=True)
class AuditEvent:
    id: AuditId
    action: AuditAction
    caregiver_id: CaregiverId
    subject_ref: str
    provenance: Provenance
    detail: tuple[tuple[str, str], ...] = ()
