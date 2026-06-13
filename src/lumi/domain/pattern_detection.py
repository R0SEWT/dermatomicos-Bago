"""Deterministic longitudinal pattern detection (no AI, no causal claims).

This module turns a dependent's timeline (observations + treatment mentions)
into ``CandidatePattern`` proposals. It is the engine behind the product's
"magic moment", but it never asserts causality: it only reports temporal
coincidence ("coincide con") and repetition with a 1-2 day lag ("se repitio
despues de"), always marked ``to_validate`` for the clinician.

Safety design:

- Every statement is built through :meth:`CandidatePattern.build`, so the
  wording comes from the approved template registry and slot values are screened
  by ``assert_no_causal_language``. A slot that smuggles causal/diagnostic
  language raises ``CausalLanguageError``; we drop that candidate rather than
  surface unsafe copy.
- Slot phrases are curated, not free caregiver prose. Symptoms map to a fixed
  vocabulary; exposures prefer a short recorded value and fall back to a curated
  category phrase.
- The detector is pure and deterministic: same timeline in, same patterns out
  (results are ordered by repetition count, then alphabetically).
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from datetime import date

from .checkin import Observation
from .enums import TreatmentSource
from .errors import CausalLanguageError
from .patterns import CandidatePattern, PatternTemplate
from .provenance import Provenance
from .treatment import TreatmentMention

# Symptom/discomfort categories share the report's evolution vocabulary so the
# panel and the patterns stay consistent. Each maps to a fixed, neutral phrase.
_SYMPTOM_PHRASES: dict[str, str] = {
    "scratching": "el rascado nocturno",
    "observed_scratching": "el rascado nocturno",
    "irritability": "la irritabilidad",
}

# Tokens in a ``sleep`` observation value that mark an adverse night.
_ADVERSE_SLEEP_TOKENS: tuple[str, ...] = (
    "mal", "poco", "interrump", "fragment", "despert", "no durmio",
)
_SLEEP_PHRASE = "el sueno interrumpido"

# Exposure categories and the curated phrase used when no specific value exists.
_EXPOSURE_DEFAULTS: dict[str, str] = {
    "food": "un alimento nuevo", "comida": "un alimento nuevo",
    "clothing": "un cambio de ropa", "ropa": "un cambio de ropa",
    "detergent": "un detergente nuevo", "detergente": "un detergente nuevo",
    "environment": "un cambio en el ambiente", "ambiente": "un cambio en el ambiente",
    "product": "un producto nuevo", "producto": "un producto nuevo",
    "bath": "un cambio en el bano", "bano": "un cambio en el bano",
    "soap": "un jabon nuevo", "jabon": "un jabon nuevo",
    "exposure": "una exposicion", "exposicion": "una exposicion",
}

_LAG_DAYS = (1, 2)  # exposure on day D, symptom on D+1 or D+2
_MIN_REPETITIONS = 2  # a pair must recur to be reported
_DEFAULT_MAX_PATTERNS = 3


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip()


def _symptom_phrase(observation: Observation) -> str | None:
    category = observation.category.lower()
    if category in _SYMPTOM_PHRASES:
        return _SYMPTOM_PHRASES[category]
    if category == "sleep":
        value = _normalize(observation.value_text)
        if any(token in value for token in _ADVERSE_SLEEP_TOKENS):
            return _SLEEP_PHRASE
    return None


def _exposure_phrase(category: str, value_text: str) -> str | None:
    category = category.lower()
    if category not in _EXPOSURE_DEFAULTS:
        return None
    value = value_text.strip()
    # Prefer a short, specific recorded value (e.g. "jabon nuevo"); otherwise a
    # curated category phrase. ``build`` still screens the final slot value.
    if value and len(value) <= 40:
        return value
    return _EXPOSURE_DEFAULTS[category]


def _events(
    observations: tuple[Observation, ...],
    mentions: tuple[TreatmentMention, ...],
) -> tuple[list[tuple[date, str]], list[tuple[date, str]]]:
    """Return (symptom_events, exposure_events) as (date, phrase) lists."""
    symptoms: list[tuple[date, str]] = []
    exposures: list[tuple[date, str]] = []
    for obs in observations:
        on = obs.provenance.recorded_at.date()
        symptom = _symptom_phrase(obs)
        if symptom is not None:
            symptoms.append((on, symptom))
        exposure = _exposure_phrase(obs.category, obs.value_text)
        if exposure is not None:
            exposures.append((on, exposure))
    # A non-prescribed remedy is itself an introduced exposure.
    for mention in mentions:
        if mention.source is TreatmentSource.NON_PRESCRIBED:
            value = mention.text.strip()
            if value:
                exposures.append((
                    mention.provenance.recorded_at.date(),
                    value if len(value) <= 40 else "un remedio no prescrito",
                ))
    return symptoms, exposures


def _safe_build(
    template: PatternTemplate, slots: dict[str, str], provenance: Provenance,
    locale: str,
) -> CandidatePattern | None:
    """Build a pattern, dropping it if a slot trips the causal-language guard."""
    try:
        return CandidatePattern.build(template, slots, provenance, locale=locale)
    except CausalLanguageError:
        return None


def detect_candidate_patterns(
    observations: tuple[Observation, ...],
    mentions: tuple[TreatmentMention, ...],
    *,
    provenance: Provenance,
    locale: str = "es-PE",
    max_patterns: int = _DEFAULT_MAX_PATTERNS,
) -> tuple[CandidatePattern, ...]:
    """Detect non-causal coincidence/repetition patterns from a timeline.

    - ``REPEATED_AFTER``: an exposure precedes the same symptom by 1-2 days,
      recurring at least :data:`_MIN_REPETITIONS` times.
    - ``COINCIDES_WITH``: an exposure and a symptom share a day, recurring at
      least :data:`_MIN_REPETITIONS` times (and not already reported as a lag).
    - ``MISSING_INFO``: repeated discomfort but no exposure recorded nearby.

    Results are ordered by recurrence (desc), then by rendered text, and capped
    at ``max_patterns``.
    """
    symptoms, exposures = _events(observations, mentions)

    # Count, per (symptom, exposure) phrase pair, how many distinct symptom
    # events are preceded (lag) or accompanied (same-day) by that exposure.
    lagged: dict[tuple[str, str], set[int]] = defaultdict(set)
    same_day: dict[tuple[str, str], set[int]] = defaultdict(set)
    for i, (s_date, s_phrase) in enumerate(symptoms):
        for e_date, e_phrase in exposures:
            delta = (s_date - e_date).days
            if delta in _LAG_DAYS:
                lagged[(s_phrase, e_phrase)].add(i)
            elif delta == 0:
                same_day[(s_phrase, e_phrase)].add(i)

    patterns: list[tuple[int, CandidatePattern]] = []
    reported_pairs: set[tuple[str, str]] = set()

    for (symptom, exposure), hits in lagged.items():
        if len(hits) >= _MIN_REPETITIONS:
            built = _safe_build(
                PatternTemplate.REPEATED_AFTER,
                {"symptom": symptom, "exposure": exposure}, provenance, locale,
            )
            if built is not None:
                patterns.append((len(hits), built))
                reported_pairs.add((symptom, exposure))

    for (symptom, exposure), hits in same_day.items():
        if (symptom, exposure) in reported_pairs:
            continue
        if len(hits) >= _MIN_REPETITIONS:
            built = _safe_build(
                PatternTemplate.COINCIDES_WITH,
                {"symptom": symptom, "exposure": exposure}, provenance, locale,
            )
            if built is not None:
                patterns.append((len(hits), built))

    # Honesty: repeated discomfort with no exposure logged nearby -> flag the gap.
    if not patterns and len(symptoms) >= _MIN_REPETITIONS and not exposures:
        built = _safe_build(
            PatternTemplate.MISSING_INFO,
            {"topic": "exposiciones recientes (alimentos, ropa, productos)"},
            provenance, locale,
        )
        if built is not None:
            patterns.append((0, built))

    patterns.sort(key=lambda pair: (-pair[0], pair[1].rendered))
    return tuple(pattern for _, pattern in patterns[:max_patterns])
