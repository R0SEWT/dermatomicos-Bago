"""Local speech-to-text via faster-whisper (CTranslate2). Optional ``[voice]``.

faster-whisper runs Whisper on CTranslate2 — local, free, no network at
inference, and notably no PyTorch dependency (lighter than the reference
implementation, coherent with keeping the Lumi runtime slim). The import is
deferred into ``__init__`` so the core never imports ctranslate2 just by
importing this module's package.

Spanish is forced (``language="es"``) since the product is es-PE; the model
still handles the regional accent. Audio bytes are written to a temp file
because CTranslate2 reads from a path.
"""

from __future__ import annotations

import os
import tempfile

from ...ports.transcription import Transcript, VoiceClip

_SUFFIX_BY_MIME = {
    "audio/ogg": ".ogg",
    "audio/opus": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/webm": ".webm",
}


class FasterWhisperTranscriber:
    """Transcriber backed by a locally-loaded faster-whisper model.

    ``model_size`` defaults to ``small`` (good es quality, CPU-friendly); set
    ``LUMI_VOICE_MODEL`` to override (e.g. ``tiny``/``base``/``medium``).
    """

    def __init__(
        self,
        model_size: str | None = None,
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        from faster_whisper import WhisperModel  # deferred: optional [voice] dep

        size = model_size or os.environ.get("LUMI_VOICE_MODEL", "small")
        self._model = WhisperModel(size, device=device, compute_type=compute_type)

    def transcribe(self, clip: VoiceClip) -> Transcript:
        suffix = _SUFFIX_BY_MIME.get(clip.mime, ".ogg")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(clip.data)
            path = handle.name
        try:
            segments, info = self._model.transcribe(
                path, language="es", beam_size=5, vad_filter=True
            )
            text = "".join(segment.text for segment in segments).strip()
        finally:
            os.unlink(path)
        return Transcript(
            text=text,
            language=getattr(info, "language", "es") or "es",
            confidence=getattr(info, "language_probability", None),
            duration_s=getattr(info, "duration", clip.duration_s),
        )
