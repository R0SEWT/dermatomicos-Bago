"""Azure OpenAI transcription adapter (fake client, no network, no model)."""

from types import SimpleNamespace

import pytest

from lumi.adapters.media.azure_whisper import (
    AzureWhisperSettings,
    AzureWhisperTranscriber,
)
from lumi.ports.transcription import Transcript, VoiceClip


class FakeTranscriptions:
    def __init__(self, text):
        self._text = text
        self.kwargs = None
        self.filename = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        self.filename = getattr(kwargs.get("file"), "name", None)
        return SimpleNamespace(text=self._text)


class FakeClient:
    def __init__(self, text):
        self.transcriptions = FakeTranscriptions(text)
        self.audio = SimpleNamespace(transcriptions=self.transcriptions)


def _settings(**over):
    base = {"endpoint": "https://resource.openai.azure.com", "deployment": "whisper"}
    base.update(over)
    return AzureWhisperSettings(**base)


def test_transcribe_uploads_audio_and_returns_stripped_text():
    client = FakeClient("  anoche se rascó mucho  ")
    transcriber = AzureWhisperTranscriber(_settings(language="es"), client)

    out = transcriber.transcribe(
        VoiceClip(data=b"OggS-bytes", mime="audio/ogg", duration_s=9.0)
    )

    assert isinstance(out, Transcript)
    assert out.text == "anoche se rascó mucho"  # stripped
    assert out.language == "es"
    assert out.duration_s == 9.0
    # the deployment is the model, language is forwarded, and the raw audio is sent
    assert client.transcriptions.kwargs["model"] == "whisper"
    assert client.transcriptions.kwargs["language"] == "es"
    assert client.transcriptions.kwargs["file"].read() == b"OggS-bytes"
    assert client.transcriptions.filename.endswith(".ogg")  # mime -> filename suffix


def test_webm_recording_maps_to_webm_suffix():
    client = FakeClient("ok")
    AzureWhisperTranscriber(_settings(), client).transcribe(
        VoiceClip(data=b"x", mime="audio/webm")
    )
    assert client.transcriptions.filename.endswith(".webm")


def test_unknown_mime_defaults_to_ogg_suffix():
    client = FakeClient("ok")
    AzureWhisperTranscriber(_settings(), client).transcribe(
        VoiceClip(data=b"x", mime="audio/weird")
    )
    assert client.transcriptions.filename.endswith(".ogg")


def test_settings_require_endpoint_and_deployment(monkeypatch):
    for var in (
        "AZURE_AI_ENDPOINT",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT",
    ):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError):
        AzureWhisperSettings.from_env()


def test_settings_from_env_reuses_azure_surface_without_storing_key(monkeypatch):
    monkeypatch.delenv("LUMI_VOICE_LANGUAGE", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://r.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT", "whisper")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "must-not-be-read")

    settings = AzureWhisperSettings.from_env()

    assert settings.deployment == "whisper"
    assert settings.base_url.endswith("/openai/v1/")
    assert settings.use_api_key is True
    assert settings.language == "es"
    assert not hasattr(settings, "api_key")  # the key is never stored on the settings
