"""Transcription port + canned demo adapter (fast, no speech model)."""

from lumi.adapters.media.canned import CannedTranscriber
from lumi.api.voice_samples import DEMO_VOICE_NOTES, VoiceNote, demo_transcript_map
from lumi.ports.transcription import Transcript, VoiceClip


def test_canned_transcriber_resolves_reference():
    transcriber = CannedTranscriber({"a": "hola"}, default="?")
    out = transcriber.transcribe(VoiceClip(data=b"", reference="a", duration_s=3.0))
    assert isinstance(out, Transcript)
    assert out.text == "hola"
    assert out.language == "es"
    assert out.duration_s == 3.0


def test_canned_transcriber_falls_back_to_default():
    transcriber = CannedTranscriber({"a": "hola"}, default="(sin audio)")
    assert transcriber.transcribe(VoiceClip(data=b"", reference="zzz")).text == "(sin audio)"


def test_demo_samples_have_unique_ids_and_nonempty_transcripts():
    ids = [note.id for note in DEMO_VOICE_NOTES]
    assert len(ids) == len(set(ids))
    assert all(note.transcript.strip() for note in DEMO_VOICE_NOTES)
    assert all(note.seconds > 0 for note in DEMO_VOICE_NOTES)


def test_demo_transcript_map_matches_samples():
    assert demo_transcript_map() == {n.id: n.transcript for n in DEMO_VOICE_NOTES}


def test_voice_note_duration_is_mm_ss():
    assert VoiceNote("x", 9, "t").duration == "0:09"
    assert VoiceNote("x", 75, "t").duration == "1:15"
