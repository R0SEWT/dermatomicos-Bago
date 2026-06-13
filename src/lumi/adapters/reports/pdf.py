"""Clinician report rendering as HTML and PDF.

Two stages so each is independently testable and the heavy dependency stays
optional:

- :func:`render_clinician_report_html` turns a :class:`ClinicianReport` into a
  deterministic, self-contained HTML string using Jinja2 (autoescaped). Content
  assertions (sections present, non-prescribed kept separate, disclaimer, no
  causal wording) test this layer without any system libraries.
- :func:`render_clinician_report_pdf` renders that HTML to PDF bytes with
  WeasyPrint. WeasyPrint (and its pango/cairo system stack) lives behind the
  ``report`` extra and is imported lazily, so importing this module — and
  rendering HTML — never requires the extra.

Determinism: the content is a pure function of the report. WeasyPrint stamps the
PDF with a creation date by default; set ``SOURCE_DATE_EPOCH`` for byte-for-byte
reproducible PDFs (reproducible-builds convention).

Safety: this is a faithful renderer, not an author. Every dynamic value comes
from already-validated domain records — ``CandidatePattern.rendered`` is screened
for causal/diagnostic language at build time, and non-prescribed items render in
their own neutral section, never merged with the prescribed plan.
"""

from __future__ import annotations

from datetime import date, datetime

from jinja2 import Environment, select_autoescape

from ...domain.report import ClinicianReport

_PATTERNS_NOTE = "A conversar y validar con el medico tratante. No son diagnostico."

_TEMPLATE_SOURCE = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Reporte clinico Lumi</title>
<style>
  @page { size: A4; margin: 18mm 16mm; }
  body { font-family: "DejaVu Sans", "Helvetica", sans-serif; color: #1c1c1c;
         font-size: 11pt; line-height: 1.4; }
  h1 { font-size: 18pt; margin: 0 0 2mm; }
  .meta { color: #555; font-size: 9.5pt; margin-bottom: 6mm; }
  .meta span { display: block; }
  h2 { font-size: 12.5pt; border-bottom: 1px solid #ddd; padding-bottom: 1mm;
       margin: 6mm 0 2mm; }
  ul { margin: 0; padding-left: 5mm; }
  li { margin: 0.6mm 0; }
  .empty { color: #888; font-style: italic; }
  .badge { display: inline-block; font-size: 8.5pt; font-weight: 600;
           color: #7a4b00; background: #fff3df; border: 1px solid #f0d9af;
           border-radius: 3px; padding: 0 4px; margin-left: 4px; }
  .note { color: #555; font-size: 9.5pt; margin: 1mm 0 2mm; }
  .nonrx { background: #fafafa; border: 1px solid #eee; border-radius: 4px;
           padding: 2mm 3mm; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 0.8mm 0; vertical-align: top; }
  td.day { width: 26mm; color: #555; white-space: nowrap; }
  td.cat { width: 34mm; color: #333; }
  .disclaimer { margin-top: 8mm; padding-top: 3mm; border-top: 1px solid #ddd;
                color: #555; font-size: 9pt; }
</style>
</head>
<body>
  <h1>Reporte clinico Lumi</h1>
  <div class="meta">
    <span>Generado: {{ generated }}</span>
    <span>Plan: {{ plan_ref }}</span>
    <span>Politica de seguridad: {{ policy_version }}</span>
  </div>

  <h2>Plan prescrito activo</h2>
  {% if plan_items %}
  <ul>{% for text in plan_items %}<li>{{ text }}</li>{% endfor %}</ul>
  {% else %}<p class="empty">Sin plan activo registrado.</p>{% endif %}

  <h2>Evolucion observada (sintoma y sueno)</h2>
  {% if evolution %}
  <table>{% for day, category, note in evolution %}
    <tr><td class="day">{{ day }}</td><td class="cat">{{ category }}</td>
        <td>{{ note }}</td></tr>{% endfor %}
  </table>
  {% else %}<p class="empty">Sin observaciones registradas.</p>{% endif %}

  <h2>Adherencia al plan prescrito</h2>
  {% if adherence %}
  <ul>{% for text, count in adherence %}
    <li>{{ text }} - {{ count }} registro{{ "s" if count != 1 else "" }}</li>
  {% endfor %}</ul>
  {% else %}<p class="empty">Sin items prescritos para medir adherencia.</p>{% endif %}

  <h2>Patrones a validar <span class="badge">a validar</span></h2>
  <p class="note">{{ patterns_note }}</p>
  {% if patterns %}
  <ul>{% for text in patterns %}<li>{{ text }}</li>{% endfor %}</ul>
  {% else %}<p class="empty">Sin patrones repetidos detectados en el periodo.</p>{% endif %}

  <h2>Productos o remedios no prescritos</h2>
  <div class="nonrx">
  {% if non_prescribed %}
  <ul>{% for text in non_prescribed %}<li>{{ text }}</li>{% endfor %}</ul>
  {% else %}<p class="empty">Ninguno registrado.</p>{% endif %}
  </div>

  <h2>Fotos (documentacion, ordenadas por fecha)</h2>
  {% if photos %}
  <ul>{% for day in photos %}<li>{{ day }}</li>{% endfor %}</ul>
  {% else %}<p class="empty">Sin fotos registradas.</p>{% endif %}

  <h2>Cobertura de datos</h2>
  <ul>{% for topic, status in coverage %}
    <li>{{ topic }}: {{ status }}</li>{% endfor %}</ul>

  <p class="disclaimer">{{ disclaimer }}</p>
</body>
</html>
"""

_ENV = Environment(autoescape=select_autoescape(["html", "xml"]), trim_blocks=True)
_TEMPLATE = _ENV.from_string(_TEMPLATE_SOURCE)


def _iso_day(value: date) -> str:
    return value.isoformat()


def _build_context(report: ClinicianReport) -> dict[str, object]:
    """Flatten a report into deterministic, pre-formatted template values."""
    if report.plan_version_id is not None:
        plan_ref = (
            f"{report.plan_id} / version {report.plan_version_number} "
            f"({report.plan_version_id})"
        )
    else:
        plan_ref = "Sin plan activo"

    generated = (
        report.generated_at.isoformat(timespec="seconds")
        if isinstance(report.generated_at, datetime)
        else str(report.generated_at)
    )

    return {
        "generated": generated,
        "plan_ref": plan_ref,
        "policy_version": report.policy_version,
        "plan_items": [item.instruction_text for item in report.active_plan_items],
        "evolution": [
            (_iso_day(point.on), point.category, point.note)
            for point in report.symptom_sleep_evolution
        ],
        "adherence": [
            (line.instruction_text, line.observed_count) for line in report.adherence
        ],
        "patterns": [pattern.rendered for pattern in report.candidate_patterns],
        "patterns_note": _PATTERNS_NOTE,
        "non_prescribed": [item.text for item in report.non_prescribed_items],
        "photos": [_iso_day(photo.captured_on) for photo in report.photos],
        "coverage": [(note.topic, note.status) for note in report.coverage_notes],
        "disclaimer": report.disclaimer,
    }


def render_clinician_report_html(report: ClinicianReport) -> str:
    """Render a clinician report to a deterministic, self-contained HTML string."""
    return _TEMPLATE.render(**_build_context(report))


def render_clinician_report_pdf(report: ClinicianReport) -> bytes:
    """Render a clinician report to PDF bytes via WeasyPrint.

    Requires the ``report`` extra (``uv sync --extra report``); WeasyPrint is
    imported lazily so the core runtime and HTML rendering never depend on it.
    """
    try:
        from weasyprint import HTML  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise RuntimeError(
            "PDF rendering requires the 'report' extra: uv sync --extra report"
        ) from exc

    html = render_clinician_report_html(report)
    return HTML(string=html).write_pdf()
