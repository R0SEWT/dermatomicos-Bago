"""Speech-to-text port: turn a caregiver voice note into untrusted text.

A voice note is just another way to author a check-in. The transcript it
produces is fed into the *same* extraction/check-in flow as a typed message and
carries the *same* trust level: it is an untrusted proposal that deterministic
code validates before anything is persisted. Transcription happens at the edge
(channel/API), before the router — the conversation core never sees audio.

The heavy speech model lives behind the optional ``[voice]`` extra; the core
depends only on this port (stdlib types), so importing it never pulls a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VoiceClip:
    """An inbound audio note awaiting transcription.

    ``data`` is the raw encoded audio (e.g. OGG/Opus from WhatsApp, or WAV).
    ``reference`` is an optional opaque tag that fixture-based adapters (demo /
    tests) may use to resolve a canned transcript; real transcribers ignore it
    and read ``data``. It is never a caregiver or child name.
    """

    data: bytes
    mime: str = "audio/ogg"
    duration_s: float | None = None
    reference: str | None = None


@dataclass(frozen=True)
class Transcript:
    """The text recovered from a voice note, plus light provenance metadata.

    ``text`` is untrusted: it flows into the normal extraction path and is never
    treated as authoritative on its own.
    """

    text: str
    language: str = "es"
    confidence: float | None = None
    duration_s: float | None = None


class Transcriber(Protocol):
    def transcribe(self, clip: VoiceClip) -> Transcript: ...
