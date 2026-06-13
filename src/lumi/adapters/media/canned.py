"""Deterministic, dependency-free transcriber for the demo and fast tests.

It resolves a transcript from the clip's ``reference`` against a fixed map (the
demo's sample voice notes). This lets the WhatsApp demo show the full
voice-note -> transcription -> check-in pipeline live without loading a speech
model, and lets tests exercise the integration without the ``[voice]`` extra.
It never inspects ``data`` — it is a stand-in, not a real recogniser.
"""

from __future__ import annotations

from collections.abc import Mapping

from ...ports.transcription import Transcript, VoiceClip


class CannedTranscriber:
    """Return a pre-scripted transcript keyed by ``clip.reference``."""

    def __init__(self, transcripts: Mapping[str, str], default: str = "") -> None:
        self._transcripts = dict(transcripts)
        self._default = default

    def transcribe(self, clip: VoiceClip) -> Transcript:
        text = self._transcripts.get(clip.reference or "", self._default)
        return Transcript(
            text=text, language="es", confidence=1.0, duration_s=clip.duration_s
        )
