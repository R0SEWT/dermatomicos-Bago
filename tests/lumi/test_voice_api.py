"""Voice-note endpoints: sample list + transcribe-then-route (AI off, no model)."""

import pytest

pytest.importorskip("fastapi", reason="requires the optional 'web' extra")
from starlette.testclient import TestClient  # noqa: E402

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
