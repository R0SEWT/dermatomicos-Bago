"""The provenance envelope attached to every persistable fact.

Every aggregate that gets stored embeds a required ``Provenance`` with no
default, so a fact without source/actor/time/confirmation is unrepresentable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .enums import ActorKind, ConfirmationState
from .ids import ProviderEventId


@dataclass(frozen=True)
class ExternalIdentity:
    """An opaque channel-scoped identity.

    The domain never interprets ``opaque_id`` (it may be a phone number, a
    WhatsApp BSUID, or a test id) and never assumes a phone number exists.
    Lookups key on ``(channel, opaque_id)`` so the 2026 WhatsApp BSUID change
    (empty from/to) only touches the channel adapter, never the domain.
    """

    channel: str
    opaque_id: str
    display_hint: str | None = None


@dataclass(frozen=True)
class Actor:
    """Who caused a change. ``ref`` is e.g. a caregiver id or model deployment."""

    kind: ActorKind
    ref: str


@dataclass(frozen=True)
class Provenance:
    """Source, actor, time, and confirmation state for a single fact."""

    actor: Actor
    recorded_at: datetime
    confirmation_state: ConfirmationState
    source_message_id: str | None = None
    provider_event_id: ProviderEventId | None = None
