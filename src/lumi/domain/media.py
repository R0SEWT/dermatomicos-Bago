"""Media documents (photos, voice notes). Documentation only, never inferred."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .ids import DependentId, MediaId
from .provenance import Provenance


@dataclass(frozen=True)
class MediaDocument:
    """A reference to a stored media object.

    ``blob_ref`` is an opaque id, never a caregiver/child name. Photos are
    documentation only; no vision inference happens in the MVP.
    """

    id: MediaId
    dependent_id: DependentId
    kind: str  # "photo" | "voice"
    blob_ref: str
    captured_on: date
    provenance: Provenance
