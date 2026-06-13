"""Voice-note endpoints: sample list + transcribe-then-route (AI off, no model)."""

import base64

import pytest

pytest.importorskip("fastapi", reason="requires the optional 'web' extra")
from starlette.testclient import TestClient  # noqa: E402

from lumi.adapters.media.canned import CannedTranscriber  # noqa: E402
from lumi.api.web import create_app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(create_app(use_ai=False))


def test_voice_samples_are_listed(client):
    samples = client.get("/api/voice/samples").json()["samples"]
    assert samples
    assert all("id" in s and "duration" in s for s in samples)


def test_voice_note_is_transcribed_and_recorded_as_checkin(client):
    sample_id = client.get("/api/voice/samples").json()["samples"][0]["id"]
    before = len(client.get("/api/snapshot").json()["transcript"])
    body = client.post("/api/voice", json={"id": sample_id}).json()
    assert body["transcript"]                 # canned transcript surfaced
    assert isinstance(body["reply"], str)     # routed through the check-in flow
    after = len(client.get("/api/snapshot").json()["transcript"])
    assert after == before + 2                # caregiver (voice) + lumi turns


def test_unknown_voice_note_is_404(client):
    assert client.post("/api/voice", json={"id": "no-existe"}).status_code == 404


def test_uploaded_audio_is_transcribed_and_recorded_as_checkin(client):
    # Swap in a transcriber that returns text for real audio (stands in for the
    # Azure / faster-whisper engine that the no-AI test config does not build).
    client.app.state.demo.runtime.transcriber = CannedTranscriber(
        {}, default="anoche se rascó muchísimo"
    )
    audio = base64.b64encode(b"fake-opus-bytes").decode()
    before = len(client.get("/api/snapshot").json()["transcript"])

    body = client.post(
        "/api/voice/upload",
        json={"audio_b64": audio, "mime": "audio/webm", "duration_s": 6},
    ).json()

    assert body["transcript"] == "anoche se rascó muchísimo"  # transcript surfaced
    assert body["duration"] == "0:06"  # duration rendered m:ss
    assert isinstance(body["reply"], str)  # routed through the check-in flow
    after = len(client.get("/api/snapshot").json()["transcript"])
    assert after == before + 2  # caregiver (voice) + lumi turns


def test_upload_with_no_engine_wired_records_nothing(client):
    # The no-AI config builds a no-op transcriber: real audio yields empty text
    # and no turn is recorded (honest "no engine" behaviour, not an error).
    audio = base64.b64encode(b"fake-opus-bytes").decode()
    before = len(client.get("/api/snapshot").json()["transcript"])

    body = client.post("/api/voice/upload", json={"audio_b64": audio}).json()

    assert body["transcript"] == ""
    assert body["reply"] == ""
    after = len(client.get("/api/snapshot").json()["transcript"])
    assert after == before


def test_upload_rejects_invalid_base64(client):
    r = client.post("/api/voice/upload", json={"audio_b64": "!!! not base64 !!!"})
    assert r.status_code == 422


def test_upload_rejects_empty_audio(client):
    assert client.post("/api/voice/upload", json={"audio_b64": ""}).status_code == 422
