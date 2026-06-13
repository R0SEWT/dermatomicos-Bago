"""Deterministic Spanish relative-date resolution (pure, offline, no LLM)."""

from datetime import date

import pytest

from lumi.domain.relative_dates import resolve_relative_date

# Reference is a Saturday (weekday() == 5), matching the suite's FixedClock day.
_REF = date(2026, 6, 13)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hoy durmió tranquila", _REF),
        ("ayer se rascó mucho", date(2026, 6, 12)),
        ("anteayer le di la crema", date(2026, 6, 11)),
        ("antier cambiamos el jabón", date(2026, 6, 11)),
        ("antes de ayer la bañé", date(2026, 6, 11)),
        ("hace 3 días usamos jabón nuevo", date(2026, 6, 10)),
        ("hace un día empezó", date(2026, 6, 12)),
        ("hace diez días", date(2026, 6, 3)),
    ],
)
def test_resolves_supported_expressions(text, expected):
    assert resolve_relative_date(text, _REF) == expected


def test_anteayer_wins_over_ayer_substring():
    # \b must keep "ayer" from matching inside "anteayer".
    assert resolve_relative_date("anteayer", _REF) == date(2026, 6, 11)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("el lunes pasado lo llevé", date(2026, 6, 8)),    # most recent past Monday
        ("lunes pasado", date(2026, 6, 8)),
        ("este viernes", date(2026, 6, 12)),
        ("el último jueves", date(2026, 6, 11)),
        ("el sábado pasado", date(2026, 6, 6)),            # same weekday => a week ago
        ("el domingo pasado", date(2026, 6, 7)),
    ],
)
def test_resolves_qualified_weekdays(text, expected):
    assert resolve_relative_date(text, _REF) == expected


def test_case_and_accents_are_normalized():
    assert resolve_relative_date("Anteayer", _REF) == date(2026, 6, 11)
    assert resolve_relative_date("el miércoles pasado", _REF) == date(2026, 6, 10)


@pytest.mark.parametrize(
    "text",
    [
        "durmió tranquila",                 # no temporal expression
        "durmió tranquila anoche",          # 'anoche' is intentionally NOT a day shift
        "los lunes lo baño",                # habitual bare weekday, not qualified
        "",
    ],
)
def test_returns_none_when_unsupported(text):
    assert resolve_relative_date(text, _REF) is None


def test_result_is_never_in_the_future():
    for text in ("hoy", "ayer", "anteayer", "hace 2 días", "el lunes pasado"):
        assert resolve_relative_date(text, _REF) <= _REF
