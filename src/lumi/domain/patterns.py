"""Candidate longitudinal patterns, expressed only in approved, non-causal copy.

A ``CandidatePattern`` can only be built through ``build`` which (a) renders
from the approved template table — free model prose can never become the
statement, only slot fills — and (b) rejects causal/diagnostic language in both
the rendered text and the slot values.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

from .errors import CausalLanguageError
from .provenance import Provenance


class PatternTemplate(Enum):
    COINCIDES_WITH = "coincides_with"
    REPEATED_AFTER = "repeated_after"
    MISSING_INFO = "missing_info"


# Approved, clinician-reviewable copy keyed by (template, locale). Slots are the
# only variable parts; the surrounding wording is fixed.
APPROVED_TEMPLATES: dict[tuple[PatternTemplate, str], str] = {
    (PatternTemplate.COINCIDES_WITH, "es-PE"): "{symptom} coincide con {exposure}.",
    (PatternTemplate.REPEATED_AFTER, "es-PE"): "{symptom} se repitio despues de {exposure}.",
    (PatternTemplate.MISSING_INFO, "es-PE"): "Falta informacion sobre {topic}.",
}

# Heuristic backstop. The real guard is the approved-template registry; this
# catches causal/diagnostic stems sneaking in through slot values.
FORBIDDEN_CAUSAL_STEMS: tuple[str, ...] = (
    "caus",
    "alergi",
    "diagn",
    "provoc",
    "porque",
    "debido a",
    "es por",
    "le hace dano",
    "brote confirmado",
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def assert_no_causal_language(*texts: str) -> None:
    for text in texts:
        norm = _normalize(text)
        for stem in FORBIDDEN_CAUSAL_STEMS:
            if stem in norm:
                raise CausalLanguageError(f"causal/diagnostic language not allowed: {stem!r}")


@dataclass(frozen=True)
class CandidatePattern:
    """A 'to validate' coincidence statement. Never a causal conclusion."""

    template: PatternTemplate
    slots: tuple[tuple[str, str], ...]
    rendered: str
    provenance: Provenance
    status: str = "to_validate"

    @staticmethod
    def build(
        template: PatternTemplate,
        slots: dict[str, str],
        provenance: Provenance,
        *,
        locale: str = "es-PE",
    ) -> "CandidatePattern":
        copy = APPROVED_TEMPLATES.get((template, locale))
        if copy is None:
            raise CausalLanguageError(
                f"no approved template for {template} / {locale}"
            )
        rendered = copy.format(**slots)
        assert_no_causal_language(rendered, *slots.values())
        return CandidatePattern(
            template=template,
            slots=tuple(sorted(slots.items())),
            rendered=rendered,
            provenance=provenance,
        )
