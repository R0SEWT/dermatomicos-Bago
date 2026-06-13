"""Deterministic resolution of Spanish relative-date expressions.

When a caregiver writes "anteayer le di la crema" or "el lunes lo bañé", the
event happened *before* the message. The pattern detector keys coincidence and
repetition on the event date, so dating that fact to the message date distorts
the lags behind the product's "magic moment". This pure helper normalizes the
bounded set of Spanish temporal expressions we support to an absolute date,
relative to the message date.

No LLM and no third-party dependency: the supported vocabulary is small and
fixed, mapped onto ``timedelta`` / weekday arithmetic, so the same
``(text, reference_date)`` always yields the same result — trivially testable
offline. Anything outside the vocabulary returns ``None`` and the caller keeps
the message date.

Out of scope on purpose:

- "anoche" / "anteanoche" are **not** treated as day shifts. A nightly check-in
  written about "anoche" is understood to be about its own night, so shifting it
  would corrupt the timeline rather than correct it.
- A check-in carries a single temporal anchor (MVP): if the note mixes several
  ("anteayer ... y ayer ..."), the most specific expression wins by the
  precedence below and applies to the whole note.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

# Spanish weekday names -> Monday=0 .. Sunday=6 (matches ``date.weekday()``).
_WEEKDAYS: dict[str, int] = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sabado": 5, "domingo": 6,
}

# Written small numbers accepted in "hace N días" alongside bare digits.
_WORD_NUMBERS: dict[str, int] = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}

# Relative anchors are for recent caregiver history, not arbitrary archival
# dates. Bounding numeric input also prevents malformed text from overflowing
# ``date - timedelta``.
_MAX_RELATIVE_DAYS = 365

_DAYS = "|".join(_WEEKDAYS)
_NUMS = "|".join(_WORD_NUMBERS)

# Evaluated in this order; the first to match wins, so more specific expressions
# precede looser ones. ``\b`` keeps "ayer" from matching inside "anteayer".
_HACE_N = re.compile(rf"\bhace\s+(\d+|{_NUMS})\s+dias?\b")
_ANTEAYER = re.compile(r"\b(?:anteayer|antier|antes\s+de\s+ayer)\b")
_AYER = re.compile(r"\bayer\b")
_HOY = re.compile(r"\bhoy\b")
# A weekday only counts when qualified — "el lunes", "este lunes", "último
# lunes", or "lunes pasado" — never a bare "lunes" (which is usually habitual).
_WEEKDAY = re.compile(
    rf"\b(?:(?:el|este|ultim[oa])\s+({_DAYS})(?:\s+pasad[oa])?|({_DAYS})\s+pasad[oa])\b"
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def resolve_relative_date(text: str, reference_date: date) -> date | None:
    """Resolve a Spanish temporal expression to an absolute date, or ``None``.

    ``reference_date`` is the message date. Supported: ``hoy``, ``ayer``,
    ``anteayer`` (and ``antier`` / ``antes de ayer``), ``hace N días``
    (digit or written number), and a qualified weekday (``el lunes``,
    ``este lunes``, ``último lunes``, ``lunes pasado``) which resolves to that
    weekday's most recent strictly-past occurrence. Returns ``None`` for text
    with no supported expression. The result is never in the future.
    """
    normalized = _normalize(text)

    hace = _HACE_N.search(normalized)
    if hace:
        token = hace.group(1)
        days = int(token) if token.isdigit() else _WORD_NUMBERS[token]
        if days > _MAX_RELATIVE_DAYS:
            return None
        return reference_date - timedelta(days=days)

    if _ANTEAYER.search(normalized):
        return reference_date - timedelta(days=2)
    if _AYER.search(normalized):
        return reference_date - timedelta(days=1)
    if _HOY.search(normalized):
        return reference_date

    weekday = _WEEKDAY.search(normalized)
    if weekday:
        target = _WEEKDAYS[weekday.group(1) or weekday.group(2)]
        # Step back to the most recent past occurrence; same weekday => a week ago.
        offset = (reference_date.weekday() - target) % 7 or 7
        return reference_date - timedelta(days=offset)

    return None
