"""Actual provider requests use a strict schema, with unchanged local validation."""

import json

from app.integrations.ai import OpenAiConfig, OpenAiResponsesOnboardingProvider
from app.modules.training.prescription_policy import DIMENSIONS
from app.modules.training.prescription_writer_schema import prescription_writer_schema


def test_strict_schema_supports_the_complete_typed_contract_without_open_objects():
    schema = prescription_writer_schema()

    def inspect(node):
        if isinstance(node, list):
            for child in node:
                inspect(child)
        elif isinstance(node, dict):
            assert not {"oneOf", "discriminator", "default", "propertyNames"}.intersection(node)
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for child in node.values():
                inspect(child)

    inspect(schema)
    rules = schema["$defs"]["TypedPrescriptionItem"]["properties"]["decision_rules"]
    assert set(rules["properties"]) == set(DIMENSIONS)
    provider = OpenAiResponsesOnboardingProvider(OpenAiConfig("test-not-a-secret", "test-model", 1))
    request = provider._request({}, "Test instructions", schema)
    body = json.loads(request.data)
    assert body["text"]["format"]["strict"] is True
    assert body["text"]["format"]["schema"] == schema


def test_unconfirmed_calendar_cannot_be_requested_in_the_writer_schema():
    schema = prescription_writer_schema({"confirmed_schedule": None})
    assert schema["properties"]["schedule"] == {"type": "null"}
    assert schema["properties"]["scope"] == {"type": "string", "enum": ["session_sheet"]}


def test_complete_revision_scope_is_owned_by_the_backend():
    schema = prescription_writer_schema(
        {"confirmed_schedule": {"occurrences": []}, "required_scope": "plan_revision"}
    )
    assert schema["properties"]["scope"] == {"type": "string", "enum": ["plan_revision"]}


def test_confirmed_calendar_preserves_the_typed_schedule_contract():
    schema = prescription_writer_schema({"confirmed_schedule": {"occurrences": []}})
    assert (
        schema["properties"]["schedule"] == prescription_writer_schema()["properties"]["schedule"]
    )
