"""Pydantic response schemas for Azure OpenAI structured outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

PLAN_SCHEMA_VERSION = "plan-extraction-v1"
OBSERVATION_SCHEMA_VERSION = "observation-extraction-v1"
SourceValue = Literal["prescribed", "non_prescribed", "ambiguous"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanItemSchema(StrictModel):
    description: str
    source: SourceValue
    verbatim_span: str
    confidence: float
    ambiguous_source: bool
    dose_instructions: str | None
    cadence_hint: str | None


class PlanExtractionSchema(StrictModel):
    items: list[PlanItemSchema]
    warnings: list[str]


class ObservationItemSchema(StrictModel):
    category: str
    value_text: str
    verbatim_span: str
    confidence: float
    treatment_source: SourceValue | None
    ambiguous_source: bool


class SafetySignalsSchema(StrictModel):
    age_months: int | None
    fever_c: float | None
    lethargy: bool
    poor_feeding: bool
    spreading_rash: bool
    rash_with_pus_or_blisters: bool
    breathing_difficulty: bool
    inconsolable_crying: bool


class ObservationExtractionSchema(StrictModel):
    observations: list[ObservationItemSchema]
    signals: SafetySignalsSchema
    warnings: list[str]
