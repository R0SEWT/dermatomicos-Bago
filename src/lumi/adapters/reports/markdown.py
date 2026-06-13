"""Deterministic Markdown rendering for clinician reports."""

from __future__ import annotations

from ...domain.report import ClinicianReport


def render_clinician_report(report: ClinicianReport) -> str:
    plan_ref = (
        f"{report.plan_id} / version {report.plan_version_number} ({report.plan_version_id})"
        if report.plan_version_id is not None
        else "Sin plan activo"
    )
    lines = [
        "# Reporte clinico Lumi",
        "",
        f"Generado: {report.generated_at.isoformat()}",
        f"Plan: {plan_ref}",
        f"Politica de seguridad: {report.policy_version}",
        "",
        "## Plan prescrito activo",
    ]
    lines.extend(
        f"- {item.instruction_text}" for item in report.active_plan_items
    )
    if not report.active_plan_items:
        lines.append("- Sin datos")
    lines.extend(["", "## Adherencia observada"])
    lines.extend(
        f"- {item.instruction_text}: {item.observed_count} registros"
        for item in report.adherence
    )
    if not report.adherence:
        lines.append("- Sin datos")
    lines.extend(["", "## Evolucion observada"])
    lines.extend(
        f"- {point.on.isoformat()} - {point.category}: {point.note}"
        for point in report.symptom_sleep_evolution
    )
    if not report.symptom_sleep_evolution:
        lines.append("- Sin datos")
    lines.extend(["", "## Patrones a validar"])
    lines.extend(f"- {pattern.rendered}" for pattern in report.candidate_patterns)
    if not report.candidate_patterns:
        lines.append("- Ninguno detectado")
    lines.extend(["", "## Productos no prescritos"])
    lines.extend(f"- {item.text}" for item in report.non_prescribed_items)
    if not report.non_prescribed_items:
        lines.append("- Ninguno registrado")
    lines.extend(["", "## Cobertura de datos"])
    lines.extend(f"- {note.topic}: {note.status}" for note in report.coverage_notes)
    lines.extend(["", f"> {report.disclaimer}"])
    return "\n".join(lines)
