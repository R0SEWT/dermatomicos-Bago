"""Local stdin/stdout channel adapter."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import TextIO
from uuid import uuid4

from ...domain.ids import ProviderEventId
from ...domain.provenance import ExternalIdentity
from ...ports.channel import InboundMessage, OutboundMessage


class ConsoleChannel:
    def __init__(
        self,
        identity: ExternalIdentity | None = None,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
    ) -> None:
        self.identity = identity or ExternalIdentity("console", "local-user")
        self._input = input_stream or sys.stdin
        self._output = output_stream or sys.stdout

    def receive(self) -> Iterable[InboundMessage]:
        while True:
            self._output.write("> ")
            self._output.flush()
            line = self._input.readline()
            if not line:
                return
            text = line.strip()
            if text in {"/quit", "/exit"}:
                return
            if text:
                yield InboundMessage(
                    identity=self.identity,
                    provider_event_id=ProviderEventId(f"console-{uuid4().hex}"),
                    text=text,
                    received_at=datetime.now(timezone.utc),
                )

    def send(self, message: OutboundMessage) -> None:
        self._output.write(f"{message.text}\n")
        self._output.flush()
