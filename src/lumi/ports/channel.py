"""Normalized messaging channel contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol

from ..domain.ids import ProviderEventId
from ..domain.provenance import ExternalIdentity


@dataclass(frozen=True)
class InboundMessage:
    identity: ExternalIdentity
    provider_event_id: ProviderEventId
    text: str
    received_at: datetime


@dataclass(frozen=True)
class OutboundMessage:
    identity: ExternalIdentity
    text: str


class ChannelPort(Protocol):
    def receive(self) -> Iterable[InboundMessage]: ...
    def send(self, message: OutboundMessage) -> None: ...
