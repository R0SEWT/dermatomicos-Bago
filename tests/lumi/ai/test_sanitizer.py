from lumi.adapters.ai._sanitize import sanitize_observations, sanitize_plan
from lumi.adapters.ai.schemas import (
    ObservationExtractionSchema, PlanExtractionSchema, SafetySignalsSchema,
)
from lumi.domain.enums import TreatmentSource
from lumi.ports.ai import VersionStamp

VERSION = VersionStamp("gpt-4.1", "2025-04-14", "v1", "schema-v1", "v1", "es-PE-v1")


def test_plan_sanitizer_marks_ungrounded_and_low_confidence_ambiguous():
    parsed = PlanExtractionSchema(items=[{
        "description": "Aplicar crema", "source": "prescribed",
        "verbatim_span": "texto inventado", "confidence": 0.4,
        "ambiguous_source": False, "dose_instructions": None, "cadence_hint": None,
    }], warnings=[])
    result = sanitize_plan(parsed, "El medico dijo crema", VERSION, 0.65)
    assert result.items[0].source is TreatmentSource.PRESCRIBED
    assert result.items[0].ambiguous_source is True
    assert "ungrounded_plan_span" in result.warnings


def test_observation_sanitizer_discards_causal_language():
    parsed = ObservationExtractionSchema(
        observations=[{
            "category": "food", "value_text": "la leche causo alergia",
            "verbatim_span": "la leche causo alergia", "confidence": 0.9,
            "treatment_source": None, "ambiguous_source": False,
        }],
        signals=SafetySignalsSchema(
            age_months=None, fever_c=None, lethargy=False, poor_feeding=False,
            spreading_rash=False, rash_with_pus_or_blisters=False,
            breathing_difficulty=False, inconsolable_crying=False,
        ),
        warnings=[],
    )
    result = sanitize_observations(
        parsed, "La leche causo alergia", VERSION, 0.65
    )
    assert result.observations == ()
    assert result.warnings == ("causal_language_discarded",)
