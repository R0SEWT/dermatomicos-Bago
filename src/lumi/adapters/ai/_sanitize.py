"""Convert model-shaped data into grounded, untrusted port DTOs."""

from __future__ import annotations

from ...domain.enums import TreatmentSource
from ...domain.errors import CausalLanguageError
from ...domain.patterns import assert_no_causal_language
from ...ports.ai import (
    AIPlanProposal, ObservationProposal, ProposedObservation, ProposedPlanItem,
    ProposedSafetySignals, VersionStamp,
)


def _source(value: str | None) -> TreatmentSource | None:
    if value == "prescribed":
        return TreatmentSource.PRESCRIBED
    if value == "non_prescribed":
        return TreatmentSource.NON_PRESCRIBED
    return None


def _is_grounded(span: str, source_text: str) -> bool:
    return bool(span.strip()) and span.casefold() in source_text.casefold()


def sanitize_plan(
    parsed, source_text: str, version: VersionStamp, confidence_threshold: float,
) -> AIPlanProposal:
    warnings = list(parsed.warnings)
    items: list[ProposedPlanItem] = []
    for item in parsed.items:
        grounded = _is_grounded(item.verbatim_span, source_text)
        source = _source(item.source)
        ambiguous = (
            item.ambiguous_source or source is None
            or item.confidence < confidence_threshold or not grounded
        )
        if not grounded:
            warnings.append("ungrounded_plan_span")
        items.append(ProposedPlanItem(
            description=item.description.strip(), source=source,
            verbatim_span=item.verbatim_span, confidence=item.confidence,
            ambiguous_source=ambiguous, dose_instructions=item.dose_instructions,
            cadence_hint=item.cadence_hint,
        ))
    return AIPlanProposal(tuple(items), version, tuple(dict.fromkeys(warnings)))


def sanitize_observations(
    parsed, source_text: str, version: VersionStamp, confidence_threshold: float,
) -> ObservationProposal:
    warnings = list(parsed.warnings)
    observations: list[ProposedObservation] = []
    for item in parsed.observations:
        grounded = _is_grounded(item.verbatim_span, source_text)
        try:
            assert_no_causal_language(item.value_text)
        except CausalLanguageError:
            warnings.append("causal_language_discarded")
            continue
        source = _source(item.treatment_source)
        ambiguous = (
            item.ambiguous_source
            or item.treatment_source == "ambiguous"
            or item.confidence < confidence_threshold
            or not grounded
        )
        if not grounded:
            warnings.append("ungrounded_observation_span")
        observations.append(ProposedObservation(
            category=item.category.strip(), value_text=item.value_text.strip(),
            verbatim_span=item.verbatim_span, confidence=item.confidence,
            treatment_source=source, ambiguous_source=ambiguous,
        ))
    signals = ProposedSafetySignals(**parsed.signals.model_dump())
    return ObservationProposal(
        tuple(observations), signals, version, tuple(dict.fromkeys(warnings))
    )
