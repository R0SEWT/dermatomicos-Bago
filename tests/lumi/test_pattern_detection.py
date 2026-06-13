"""Deterministic pattern detector: lag/repetition, gaps, and no causal language."""

from datetime import datetime, timedelta, timezone

from lumi.domain.checkin import Observation
from lumi.domain.enums import ActorKind, ConfirmationState, TreatmentSource
from lumi.domain.pattern_detection import detect_candidate_patterns
from lumi.domain.patterns import PatternTemplate, assert_no_causal_language
from lumi.domain.provenance import Actor, Provenance
from lumi.domain.treatment import TreatmentMention

_BASE = datetime(2026, 6, 1, 21, 0, tzinfo=timezone.utc)
_PROV = Provenance(Actor(ActorKind.SYSTEM, "lumi"), _BASE, ConfirmationState.CONFIRMED)


def _day(offset: int) -> datetime:
    return _BASE + timedelta(days=offset)


def _obs(category: str, value: str, offset: int) -> Observation:
    prov = Provenance(
        Actor(ActorKind.CAREGIVER, "c"), _day(offset), ConfirmationState.CONFIRMED
    )
    return Observation("o", "dep", category, value, prov)


def test_repeated_after_fires_on_lagged_exposure():
    observations = (
        _obs("exposure", "jabon nuevo", 0),
        _obs("scratching", "mucho rascado", 1),   # +1 day
        _obs("exposure", "jabon nuevo", 3),
        _obs("scratching", "mucho rascado", 5),   # +2 days
    )
    patterns = detect_candidate_patterns(observations, (), provenance=_PROV)

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.template is PatternTemplate.REPEATED_AFTER
    assert pattern.status == "to_validate"
    assert "se repitio despues de" in pattern.rendered
    assert "jabon nuevo" in pattern.rendered
    assert "el rascado nocturno" in pattern.rendered


def test_no_pattern_below_threshold():
    observations = (
        _obs("exposure", "jabon nuevo", 0),
        _obs("scratching", "mucho rascado", 1),    # single occurrence only
    )
    assert detect_candidate_patterns(observations, (), provenance=_PROV) == ()


def test_non_prescribed_mention_counts_as_exposure():
    mentions = (
        TreatmentMention(
            "m1", "dep", TreatmentSource.NON_PRESCRIBED, "crema de hierbas",
            Provenance(Actor(ActorKind.CAREGIVER, "c"), _day(0), ConfirmationState.CONFIRMED),
        ),
        TreatmentMention(
            "m2", "dep", TreatmentSource.NON_PRESCRIBED, "crema de hierbas",
            Provenance(Actor(ActorKind.CAREGIVER, "c"), _day(3), ConfirmationState.CONFIRMED),
        ),
    )
    observations = (_obs("irritability", "irritable", 1), _obs("irritability", "irritable", 4))
    patterns = detect_candidate_patterns(observations, mentions, provenance=_PROV)

    assert len(patterns) == 1
    assert patterns[0].template is PatternTemplate.REPEATED_AFTER
    assert "crema de hierbas" in patterns[0].rendered


def test_missing_info_when_discomfort_without_exposure():
    observations = (
        _obs("scratching", "mucho rascado", 1),
        _obs("scratching", "mucho rascado", 4),
    )
    patterns = detect_candidate_patterns(observations, (), provenance=_PROV)

    assert len(patterns) == 1
    assert patterns[0].template is PatternTemplate.MISSING_INFO


def test_causal_exposure_value_is_dropped():
    # A slot value carrying causal/diagnostic language must never surface; the
    # candidate is silently dropped rather than rendered.
    observations = (
        _obs("exposure", "alergia al jabon", 0),
        _obs("scratching", "rascado", 1),
        _obs("exposure", "alergia al jabon", 3),
        _obs("scratching", "rascado", 4),
    )
    assert detect_candidate_patterns(observations, (), provenance=_PROV) == ()


def test_output_never_contains_causal_language():
    observations = (
        _obs("exposure", "jabon nuevo", 0),
        _obs("scratching", "rascado", 1),
        _obs("exposure", "jabon nuevo", 3),
        _obs("scratching", "rascado", 4),
    )
    for pattern in detect_candidate_patterns(observations, (), provenance=_PROV):
        assert_no_causal_language(pattern.rendered, *(v for _, v in pattern.slots))
