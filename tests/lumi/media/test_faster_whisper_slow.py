"""Real faster-whisper adapter (slow, optional ``[voice]`` extra).

Generates a short synthetic clip and asserts the adapter loads a model and
returns a well-formed ``Transcript`` without raising. It does NOT assert
specific words: a committed es-PE speech fixture is needed for that (tracked as
a follow-up). Marked slow; skipped unless faster-whisper is installed.
"""

import io
import math
import struct
import wave

import pytest

pytest.importorskip("faster_whisper", reason="requires the optional 'voice' extra")

from lumi.adapters.media.faster_whisper import FasterWhisperTranscriber  # noqa: E402
from lumi.ports.transcription import Transcript, VoiceClip  # noqa: E402


def _sine_wav_bytes(seconds: float = 1.0, freq: float = 220.0, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        frames = bytearray()
        for i in range(int(seconds * rate)):
            sample = int(3000 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", sample)
        writer.writeframes(bytes(frames))
    return buffer.getvalue()


@pytest.mark.slow
def test_faster_whisper_returns_wellformed_transcript():
    transcriber = FasterWhisperTranscriber(model_size="tiny")
    clip = VoiceClip(data=_sine_wav_bytes(), mime="audio/wav", duration_s=1.0)
    result = transcriber.transcribe(clip)
    assert isinstance(result, Transcript)
    assert isinstance(result.text, str)
    assert result.language
