from datetime import datetime, timezone

from lumi.api.router import ConversationRouter, ConversationSession
from lumi.domain.ids import ProviderEventId
from lumi.domain.provenance import ExternalIdentity
from lumi.ports.channel import InboundMessage


def _message(identity, number, text):
    return InboundMessage(
        identity, ProviderEventId(f"provider-{number}"), text,
        datetime(2026, 6, 13, 12, number, tzinfo=timezone.utc),
    )


def test_console_slice_routes_plan_checkin_report_export_delete(app, store):
    identity = ExternalIdentity("console", "bsuid-user")
    session = ConversationSession(identity)
    router = ConversationRouter(app)
    assert "Perfil creado" in router.route(_message(identity, 1, "/start bebe 2025-01"), session)
    assert "Plan propuesto" in router.route(
        _message(identity, 2, "/plan crema indicada|np:manzanilla"), session
    )
    assert "Plan confirmado" in router.route(_message(identity, 3, "/confirm 1"), session)
    safety = router.route(
        _message(identity, 4, "/checkin durmio poco; sleep=poco; respiracion=si"),
        session,
    )
    assert "atencion medica" in safety
    report = router.route(_message(identity, 5, "/report"), session)
    assert "# Reporte clinico Lumi" in report
    assert "version 1" in report
    assert "1 check-ins" in router.route(_message(identity, 6, "/export"), session)
    assert "Datos eliminados" in router.route(_message(identity, 7, "/delete"), session)
    assert session.caregiver_id is None
    assert store.caregivers == {}


def test_router_replay_does_not_duplicate(app, store):
    identity = ExternalIdentity("console", "same-user")
    session = ConversationSession(identity)
    router = ConversationRouter(app)
    message = _message(identity, 1, "/start bebe")
    first = router.route(message, session)
    second = router.route(message, session)
    assert first == second
    assert len(store.caregivers) == 1
    assert len(store.dependents) == 1


def test_free_text_without_slash_is_recorded_as_checkin(app, store):
    # No AI configured -> the raw note is recorded as a check-in (no slash needed).
    identity = ExternalIdentity("web", "nl-user")
    session = ConversationSession(identity)
    router = ConversationRouter(app)
    router.route(_message(identity, 1, "/start bebe"), session)
    reply = router.route(_message(identity, 2, "Sofia durmio mal y se rasco"), session)
    assert "registr" in reply.lower()
    assert len(store.checkins) == 1


def test_markdown_renderer_keeps_non_prescribed_separate(app):
    identity = ExternalIdentity("console", "render-user")
    session = ConversationSession(identity)
    router = ConversationRouter(app)
    router.route(_message(identity, 1, "/start bebe"), session)
    router.route(_message(identity, 2, "/plan crema"), session)
    router.route(_message(identity, 3, "/confirm"), session)
    rendered = router.route(_message(identity, 4, "/report"), session)
    assert "## Plan prescrito activo" in rendered
    assert "## Productos no prescritos" in rendered
