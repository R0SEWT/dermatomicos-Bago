"""Red-flag rule set v1.

PLACEHOLDER — requires clinical review before any user-facing pilot (RISK CL-03).
Copy is in Peruvian Spanish and always biases toward professional consultation;
it never tells a caregiver that waiting is safe.
"""

from __future__ import annotations

from ...domain.enums import SafetyDisposition
from ..rules import Condition, RedFlagRule, RuleSet

RULESET_V1 = RuleSet(
    version="redflag-v1",
    rules=(
        RedFlagRule(
            id="breathing",
            all_of=(Condition("breathing_difficulty", "is_true"),),
            disposition=SafetyDisposition.URGENT_CARE,
            approved_copy_key="urgent",
            rationale="Dificultad respiratoria requiere atencion inmediata.",
        ),
        RedFlagRule(
            id="lethargy",
            all_of=(Condition("lethargy", "is_true"),),
            disposition=SafetyDisposition.URGENT_CARE,
            approved_copy_key="urgent",
            rationale="Letargo/decaimiento marcado requiere evaluacion urgente.",
        ),
        RedFlagRule(
            id="young_infant_fever",
            all_of=(
                Condition("age_months", "<", 3),
                Condition("fever_c", ">=", 38.0),
            ),
            disposition=SafetyDisposition.URGENT_CARE,
            approved_copy_key="urgent",
            rationale="Fiebre en menor de 3 meses requiere evaluacion urgente.",
        ),
        RedFlagRule(
            id="high_fever",
            all_of=(Condition("fever_c", ">=", 39.0),),
            disposition=SafetyDisposition.CONTACT_CLINICIAN,
            approved_copy_key="contact",
            rationale="Fiebre alta debe ser consultada con el medico.",
        ),
        RedFlagRule(
            id="infected_rash",
            all_of=(Condition("rash_with_pus_or_blisters", "is_true"),),
            disposition=SafetyDisposition.CONTACT_CLINICIAN,
            approved_copy_key="contact",
            rationale="Lesiones con pus/ampollas pueden indicar sobreinfeccion.",
        ),
        RedFlagRule(
            id="spreading_rash",
            all_of=(Condition("spreading_rash", "is_true"),),
            disposition=SafetyDisposition.CONTACT_CLINICIAN,
            approved_copy_key="contact",
            rationale="Empeoramiento/extension rapida debe consultarse.",
        ),
    ),
    approved_copy=(
        (
            "urgent",
            "Por lo que describes, te sugiero buscar atencion medica de "
            "inmediato. Lo registre para tu consulta.",
        ),
        (
            "contact",
            "Te sugiero comunicarte con tu pediatra para revisarlo. Lo registre "
            "para tu consulta.",
        ),
        (
            "continue",
            "Lo registre. Seguimos observando; cualquier cambio importante "
            "consultalo con tu pediatra.",
        ),
    ),
)
