"""FastAPI backend for the Lumi demo (chat + live clinical panel).

A thin HTTP layer over the existing conversation runtime: it owns one in-process
demo session, routes chat messages through :class:`ConversationRouter`, and
exposes a clinical snapshot assembled from the application's own report/export
use cases (it never reaches into the repository directly).
"""

from __future__ import annotations

import base64
import binascii
import html
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from ..adapters.reports.markdown import render_clinician_report
from ..application.commands import BuildClinicianReport, ExportCaregiverData
from ..domain.ids import ProviderEventId
from ..ports.channel import InboundMessage
from ..ports.transcription import VoiceClip
from .bootstrap import DemoRuntime, build_runtime, load_env
from .seed import ChatTurn, seed_demo
from .voice_samples import DEMO_VOICE_NOTES, SAMPLES_BY_ID

_STATIC = Path(__file__).parent / "static"


class MessageIn(BaseModel):
    text: str


class VoiceIn(BaseModel):
    id: str


class VoiceUploadIn(BaseModel):
    """A real recorded voice note: base64 audio + its container type/length."""

    audio_b64: str
    mime: str = "audio/webm"
    duration_s: float | None = None


@dataclass
class DemoState:
    """One in-process demo conversation: runtime + chat transcript."""

    use_ai: bool
    runtime: DemoRuntime
    transcript: list[ChatTurn] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def create(cls, use_ai: bool) -> "DemoState":
        runtime = build_runtime(use_ai=use_ai)
        result = seed_demo(runtime)
        return cls(use_ai=use_ai, runtime=runtime, transcript=list(result.transcript))

    def reset(self) -> None:
        runtime = build_runtime(use_ai=self.use_ai)
        result = seed_demo(runtime)
        self.runtime = runtime
        self.transcript = list(result.transcript)


def _snapshot(state: DemoState) -> dict:
    """Assemble the clinical panel from the application's report + export."""
    app = state.runtime.application
    dependent_id = state.runtime.session.dependent_id
    caregiver_id = state.runtime.session.caregiver_id
    if dependent_id is None or caregiver_id is None:
        return {}

    report = app.build_clinician_report(BuildClinicianReport(dependent_id))
    export = app.export_caregiver_data(ExportCaregiverData(caregiver_id))
    alias = export.dependents[0].alias if export.dependents else "—"

    safety = None
    if export.safety_decisions:
        latest = export.safety_decisions[-1].evaluation
        safety = {
            "disposition": latest.disposition.value,
            "message": " ".join(latest.messages),
        }

    return {
        "alias": alias,
        "plan_version": report.plan_version_number,
        "active_plan_items": [item.instruction_text for item in report.active_plan_items],
        "adherence": [
            {"text": line.instruction_text, "count": line.observed_count}
            for line in report.adherence
        ],
        "evolution": [
            {"date": point.on.isoformat(), "category": point.category, "note": point.note}
            for point in report.symptom_sleep_evolution
        ],
        "safety": safety,
        "patterns": [
            {"rendered": p.rendered, "status": p.status, "template": p.template.value}
            for p in report.candidate_patterns
        ],
        "non_prescribed": [line.text for line in report.non_prescribed_items],
        "coverage": [
            {"topic": note.topic, "status": note.status} for note in report.coverage_notes
        ],
        "report_markdown": render_clinician_report(report),
    }


def _route(state: DemoState, text: str) -> str:
    runtime = state.runtime
    message = InboundMessage(
        runtime.session.identity, ProviderEventId(f"web-{uuid4().hex}"),
        text, runtime.clock.now(),
    )
    try:
        return runtime.router.route(message, runtime.session)
    except (ValueError, LookupError) as error:
        return str(error)


def _fmt_duration(seconds: float | None) -> str:
    """Render a clip length as ``m:ss`` for the chat bubble."""
    total = int(seconds or 0)
    return f"{total // 60}:{total % 60:02d}"


def _voice_turn(state: DemoState, text: str, duration: str) -> dict:
    """Record a transcribed voice note as a caregiver turn and route it.

    Shared by the scripted-sample and real-upload endpoints: a transcript is
    untrusted input that flows through the exact same check-in path as a typed
    message. The caller holds ``state.lock``.
    """
    state.transcript.append(ChatTurn("caregiver", text))
    reply = _route(state, text)
    state.transcript.append(ChatTurn("lumi", reply))
    return {
        "transcript": text,
        "duration": duration,
        "reply": reply,
        "snapshot": _snapshot(state),
    }


def _markdown_to_html(markdown: str) -> str:
    """Render the simple report markdown (headings, lists, quote) to safe HTML."""
    lines_out: list[str] = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("- "):
            if not in_list:
                lines_out.append("<ul>")
                in_list = True
            lines_out.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if in_list:
            lines_out.append("</ul>")
            in_list = False
        if not line:
            continue
        if line.startswith("## "):
            lines_out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            lines_out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("> "):
            lines_out.append(f"<blockquote>{html.escape(line[2:])}</blockquote>")
        else:
            lines_out.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        lines_out.append("</ul>")
    return "\n".join(lines_out)


def create_app(use_ai: bool | None = None) -> FastAPI:
    load_env()
    if use_ai is None:
        use_ai = os.environ.get("LUMI_DEMO_AI", "1") != "0"
    state = DemoState.create(use_ai=use_ai)
    app = FastAPI(title="Lumi demo")
    app.state.demo = state

    @app.get("/", response_class=HTMLResponse)
    def index() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    @app.get("/api/snapshot")
    def snapshot() -> dict:
        with state.lock:
            return {
                "ai": state.use_ai and state.runtime.ai is not None,
                "transcript": [{"role": t.role, "text": t.text} for t in state.transcript],
                "snapshot": _snapshot(state),
            }

    @app.post("/api/message")
    def message(body: MessageIn) -> dict:
        with state.lock:
            text = body.text.strip()
            if not text:
                return {"reply": "", "snapshot": _snapshot(state)}
            state.transcript.append(ChatTurn("caregiver", text))
            reply = _route(state, text)
            state.transcript.append(ChatTurn("lumi", reply))
            return {"reply": reply, "snapshot": _snapshot(state)}

    @app.get("/api/voice/samples")
    def voice_samples() -> dict:
        """Sample voice notes the demo can 'send' (id + display duration)."""
        return {
            "samples": [
                {"id": note.id, "duration": note.duration} for note in DEMO_VOICE_NOTES
            ]
        }

    @app.post("/api/voice")
    def voice(body: VoiceIn) -> dict:
        """Replay a scripted sample voice note, then route it like any message.

        Sample notes are fixtures with no audio: the transcript is resolved
        directly so the demo buttons work on stage regardless of which speech
        engine (if any) is wired. Real recorded audio goes through
        ``/api/voice/upload`` instead. The transcript is still untrusted input
        and flows through the exact same check-in path as a typed message.
        """
        note = SAMPLES_BY_ID.get(body.id)
        if note is None:
            raise HTTPException(status_code=404, detail="Nota de voz desconocida")
        with state.lock:
            return _voice_turn(state, note.transcript, note.duration)

    @app.post("/api/voice/upload")
    def voice_upload(body: VoiceUploadIn) -> dict:
        """Transcribe *real* recorded audio via the wired engine, then route it.

        Azure OpenAI transcription is preferred when configured (it reuses the
        extractor's endpoint + Entra ID); otherwise optional local faster-whisper
        or, with no engine wired, an empty transcript. The audio is transcribed
        at the edge and immediately discarded — it is never persisted. The
        recovered text is untrusted and enters the same check-in path as a typed
        message.
        """
        try:
            data = base64.b64decode(body.audio_b64, validate=True)
        except (ValueError, binascii.Error) as error:
            raise HTTPException(status_code=422, detail="audio_b64 inválido") from error
        if not data:
            raise HTTPException(status_code=422, detail="audio vacío")
        with state.lock:
            clip = VoiceClip(data=data, mime=body.mime, duration_s=body.duration_s)
            text = state.runtime.transcriber.transcribe(clip).text.strip()
            if not text:
                return {"transcript": "", "reply": "", "snapshot": _snapshot(state)}
            return _voice_turn(state, text, _fmt_duration(body.duration_s))

    @app.post("/api/reset")
    def reset() -> dict:
        with state.lock:
            state.reset()
            return {
                "transcript": [{"role": t.role, "text": t.text} for t in state.transcript],
                "snapshot": _snapshot(state),
            }

    @app.get("/api/report", response_class=HTMLResponse)
    def report() -> HTMLResponse:
        with state.lock:
            snap = _snapshot(state)
        body = _markdown_to_html(snap.get("report_markdown", ""))
        page = (
            "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            "<title>Reporte clínico Lumi</title><style>"
            "body{font:15px/1.6 system-ui,sans-serif;max-width:720px;margin:2rem auto;"
            "padding:0 1rem;color:#1f2937}h1{font-size:1.5rem}h2{font-size:1.1rem;"
            "margin-top:1.5rem;color:#0f766e}blockquote{color:#6b7280;border-left:3px "
            "solid #e5e7eb;padding-left:1rem;font-size:.9rem}ul{padding-left:1.2rem}"
            "@media print{body{margin:0}}</style></head><body>"
            f"{body}</body></html>"
        )
        return HTMLResponse(page)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    host = os.environ.get("LUMI_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("LUMI_WEB_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
