import pytest

pydantic = pytest.importorskip("pydantic")

from lumi.adapters.ai._strict_jsonschema import assert_strict_compatible  # noqa: E402
from lumi.adapters.ai.schemas import ObservationExtractionSchema, PlanExtractionSchema  # noqa: E402


def test_ai_schemas_match_azure_strict_subset():
    assert_strict_compatible(PlanExtractionSchema.model_json_schema())
    assert_strict_compatible(ObservationExtractionSchema.model_json_schema())


def test_strict_validator_rejects_optional_object_fields_and_keywords():
    with pytest.raises(ValueError, match="required"):
        assert_strict_compatible({
            "type": "object", "properties": {"name": {"type": "string"}},
            "required": [], "additionalProperties": False,
        })
    with pytest.raises(ValueError, match="unsupported"):
        assert_strict_compatible({
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 1}},
            "required": ["name"], "additionalProperties": False,
        })
