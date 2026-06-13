"""Offline validation of Azure OpenAI's strict JSON Schema subset."""

from __future__ import annotations

from collections.abc import Mapping

_FORBIDDEN = {
    "minLength", "maxLength", "pattern", "format", "minimum", "maximum",
    "multipleOf", "patternProperties", "unevaluatedProperties", "propertyNames",
    "minProperties", "maxProperties", "unevaluatedItems", "contains",
    "minContains", "maxContains", "minItems", "maxItems", "uniqueItems",
}


def assert_strict_compatible(schema: Mapping[str, object]) -> None:
    """Raise ValueError when a schema drifts outside the documented subset."""
    if "anyOf" in schema:
        raise ValueError("root schema cannot be anyOf")
    property_count = 0
    max_object_depth = 0

    def visit(node: object, object_depth: int = 0) -> None:
        nonlocal property_count, max_object_depth
        if isinstance(node, list):
            for item in node:
                visit(item, object_depth)
            return
        if not isinstance(node, Mapping):
            return
        forbidden = _FORBIDDEN.intersection(node)
        if forbidden:
            raise ValueError(f"unsupported JSON Schema keywords: {sorted(forbidden)}")
        if node.get("type") == "object" or "properties" in node:
            object_depth += 1
            max_object_depth = max(max_object_depth, object_depth)
            properties = node.get("properties", {})
            if not isinstance(properties, Mapping):
                raise ValueError("properties must be an object")
            property_count += len(properties)
            if node.get("additionalProperties") is not False:
                raise ValueError("every object must set additionalProperties=false")
            required = node.get("required")
            if set(required or ()) != set(properties):
                raise ValueError("every object property must be required")
        for key, value in node.items():
            if key != "properties":
                visit(value, object_depth)
            elif isinstance(value, Mapping):
                for child in value.values():
                    visit(child, object_depth)

    visit(schema)
    if property_count > 100:
        raise ValueError("schema exceeds 100 object properties")
    if max_object_depth > 5:
        raise ValueError("schema exceeds five object levels")
