"""Scripted voice notes for the demo.

These are the canned transcripts the demo plays when the caregiver "sends a
voice note" in the WhatsApp UI. Keeping id, duration, and transcript in one
place lets both the API (sample list + transcript map) and the demo transcriber
read a single source of truth. The phrasing is natural es-PE speech: with the
Azure extractor on, it flows through AI extraction and moves the clinical
panel; offline it is still recorded as a check-in note.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceNote:
    id: str
    seconds: int
    transcript: str

    @property
    def duration(self) -> str:
        return f"{self.seconds // 60}:{self.seconds % 60:02d}"


DEMO_VOICE_NOTES: tuple[VoiceNote, ...] = (
    VoiceNote(
        "voz-mala-noche", 9,
        "Hola, anoche Sofía se rascó muchísimo y casi no durmió, estuvo "
        "irritable toda la noche.",
    ),
    VoiceNote(
        "voz-jabon", 5,
        "Hoy en el baño volvimos a usar el jabón nuevo.",
    ),
    VoiceNote(
        "voz-fiebre", 7,
        "La siento caliente, tiene como treinta y nueve de fiebre y la noto "
        "decaída.",
    ),
)

SAMPLES_BY_ID: dict[str, VoiceNote] = {note.id: note for note in DEMO_VOICE_NOTES}


def demo_transcript_map() -> dict[str, str]:
    """``reference -> transcript`` map for the canned demo transcriber."""
    return {note.id: note.transcript for note in DEMO_VOICE_NOTES}
