"""Web demo API: snapshot, chat routing, report, reset (AI off, no network)."""

import pytest

pytest.importorskip("fastapi", reason="requires the optional 'web' extra")
from starlette.testclient import TestClient  # noqa: E402

from lumi.api.web import create_app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(create_app(use_ai=False))


def test_index_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Lumi" in response.text


def test_snapshot_exposes_seeded_clinical_state(client):
    body = client.get("/api/snapshot").json()
    assert body["ai"] is False
    assert len(body["transcript"]) >= 2

    snap = body["snapshot"]
    assert snap["alias"] == "Sofía"
    assert snap["plan_version"] == 1
    assert any("jabón nuevo" in p["rendered"] for p in snap["patterns"])
    assert all(p["status"] == "to_validate" for p in snap["patterns"])
    assert max(a["count"] for a in snap["adherence"]) >= 3
    assert snap["safety"]["disposition"] == "continue_recording"
    assert snap["non_prescribed"]


def test_message_slash_report_renders_markdown(client):
    body = client.post("/api/message", json={"text": "/report"}).json()
    assert "# Reporte clinico Lumi" in body["reply"]


def test_message_free_text_is_recorded_as_checkin(client):
    before = len(client.get("/api/snapshot").json()["transcript"])
    body = client.post(
        "/api/message", json={"text": "Anoche durmió mejor y casi no se rascó"}
    ).json()
    assert "registr" in body["reply"].lower()
    after = len(client.get("/api/snapshot").json()["transcript"])
    assert after == before + 2  # caregiver + lumi


def test_report_endpoint_returns_html(client):
    response = client.get("/api/report")
    assert response.status_code == 200
    assert "<h1>" in response.text


def test_reset_restores_seeded_transcript(client):
    seeded = len(client.get("/api/snapshot").json()["transcript"])
    client.post("/api/message", json={"text": "hola"})
    assert len(client.get("/api/snapshot").json()["transcript"]) > seeded
    reset = client.post("/api/reset").json()
    assert len(reset["transcript"]) == seeded
