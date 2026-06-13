"""Speech-to-text via Azure OpenAI Whisper. Extra ``[azure]``.

Reuses the same Azure resource and credentials as the extraction adapter:
Microsoft Entra ID by default (managed identity / ``DefaultAzureCredential``),
with an explicit ``AZURE_OPENAI_API_KEY`` fallback for local demos. Whisper is
served on Azure's classic *deployment-scoped* audio path
(``/openai/deployments/{deployment}/audio/transcriptions``), not the ``/openai/v1``
surface the chat extractor uses — so this adapter drives the ``AzureOpenAI``
client (with an ``api-version``) instead. No credentials or audio are ever
persisted or logged; the ``openai``/``azure-identity`` imports are deferred so the
core never imports them.

Transcription is the *only* thing this does; the recovered text is untrusted and
flows into the same extraction/check-in path as a typed message.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class AzureWhisperSettings:
    """Endpoint + transcription deployment, read from the shared Azure env vars."""

    endpoint: str
    deployment: str
    use_api_key: bool = False
    language: str = "es"
    api_version: str = "2024-06-01"
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "AzureWhisperSettings":
        endpoint = os.environ.get("AZURE_AI_ENDPOINT") or os.environ.get(
            "AZURE_OPENAI_ENDPOINT"
        )
        deployment = os.environ.get("AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT")
        if not endpoint or not deployment:
            raise ValueError(
                "AZURE_AI_ENDPOINT (o AZURE_OPENAI_ENDPOINT) y "
                "AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT son requeridos para Azure Whisper"
            )
        return cls(
            endpoint=endpoint,
            deployment=deployment,
            use_api_key=bool(os.environ.get("AZURE_OPENAI_API_KEY")),
            language=os.environ.get("LUMI_VOICE_LANGUAGE", "es"),
            api_version=os.environ.get(
                "AZURE_OPENAI_TRANSCRIBE_API_VERSION", "2024-06-01"
            ),
            timeout_seconds=float(os.environ.get("LUMI_AI_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.environ.get("LUMI_AI_MAX_RETRIES", "2")),
        )

    @property
    def azure_endpoint(self) -> str:
        """Bare resource endpoint. ``AzureOpenAI`` appends the deployment-scoped
        audio path itself, so the ``/openai/v1`` suffix the chat extractor may use
        is stripped here."""
        endpoint = self.endpoint.rstrip("/")
        if endpoint.endswith("/openai/v1"):
            endpoint = endpoint[: -len("/openai/v1")]
        return endpoint


class AzureWhisperTranscriber:
    """Transcriber backed by an Azure OpenAI audio-transcription deployment."""

    def __init__(self, settings: AzureWhisperSettings, client: Any | None = None) -> None:
        self._settings = settings
        if client is None:
            from openai import AzureOpenAI

            kwargs: dict[str, Any] = {
                "azure_endpoint": settings.azure_endpoint,
                "api_version": settings.api_version,
                "timeout": settings.timeout_seconds,
                "max_retries": settings.max_retries,
            }
            api_key = os.environ.get("AZURE_OPENAI_API_KEY")
            if api_key is not None:
                client = AzureOpenAI(api_key=api_key, **kwargs)
            else:
                from azure.identity import (
                    DefaultAzureCredential,
                    get_bearer_token_provider,
                )

                client = AzureOpenAI(
                    azure_ad_token_provider=get_bearer_token_provider(
                        DefaultAzureCredential(),
                        "https://cognitiveservices.azure.com/.default",
                    ),
                    **kwargs,
                )
        self._client = client

    def transcribe(self, clip: VoiceClip) -> Transcript:
        suffix = _SUFFIX_BY_MIME.get(clip.mime, ".ogg")
        upload = io.BytesIO(clip.data)
        upload.name = f"voice{suffix}"  # the SDK infers format from the filename
        response = self._client.audio.transcriptions.create(
            model=self._settings.deployment,
            file=upload,
            language=self._settings.language,
        )
        text = (getattr(response, "text", "") or "").strip()
        return Transcript(
            text=text, language=self._settings.language, duration_s=clip.duration_s
        )
