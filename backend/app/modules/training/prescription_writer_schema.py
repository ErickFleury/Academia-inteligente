"""Strict writer JSON Schema; the typed domain contract remains authoritative.

Reference: https://developers.openai.com/api/docs/guides/structured-outputs
This transport adaptation does not relax local Pydantic or prescription checks.
"""

from typing import get_args

from app.modules.training.prescription_contract import TypedPrescription
from app.modules.training.prescription_policy import Dimension


def prescription_writer_schema(context=None):
    schema = TypedPrescription.model_json_schema()
    if context is not None and "confirmed_schedule" in context:
        if context["confirmed_schedule"] is None:
            schema["properties"]["schedule"] = {"type": "null"}
            schema["properties"]["scope"] = {"type": "string", "enum": ["session_sheet"]}
            schema["properties"]["sessions"].update(minItems=1, maxItems=1)
        elif context.get("required_scope") in ("session_sheet", "plan_revision"):
            schema["properties"]["scope"] = {"type": "string", "enum": [context["required_scope"]]}
    # Every material dimension is a fixed property, never arbitrary model keys.
    schema["$defs"]["TypedPrescriptionItem"]["properties"]["decision_rules"] = {
        "type": "object",
        "properties": {
            dimension: {"type": "string", "minLength": 1} for dimension in get_args(Dimension)
        },
    }
    if context is not None:
        definitions = schema["$defs"]
        if "schema_version" in context:
            schema["properties"]["schema_version"] = {
                "type": "integer",
                "enum": [context["schema_version"]],
            }
        if "current_revision" in context:
            schema["properties"]["expected_revision"] = (
                {"type": "null"}
                if context["current_revision"] is None
                else {"type": "integer", "enum": [context["current_revision"]]}
            )
        exercises = context.get("dictionary", {}).get("exercises", [])
        if exercises:
            item_properties = definitions["TypedPrescriptionItem"]["properties"]
            definitions["TypedSession"]["properties"]["items"]["maxItems"] = min(
                100, len(exercises)
            )
            item_properties["exercise_key"] = {
                "type": "string",
                "enum": [e["key"] for e in exercises],
            }
            item_properties["variation_key"] = {
                "type": "string",
                "enum": sorted({v for e in exercises for v in e["variations"]}),
            }
            modes = {
                mode
                for exercise in exercises
                for mode in exercise.get("dose_modes", ["resistance"])
            }
            references = {
                "resistance": ["Repetitions", "Duration"],
                "aerobic": ["AerobicDose"],
                "flexibility": ["FlexibilityDose"],
                "balance": ["TaskDose"],
                "functional": ["TaskDose"],
            }
            item_properties["dose"] = {
                "anyOf": [
                    {"$ref": "#/$defs/" + key}
                    for key in sorted({key for mode in modes for key in references[mode]})
                ]
            }
            if modes == {"resistance"} and context.get("schema_version", 1) == 1:
                item_properties["rest"] = {"type": "null"}
                item_properties["group"] = {"type": "null"}
            elif "resistance" not in modes:
                item_properties["sets"] = {"type": "null"}
                item_properties["intensity"] = {"type": "null"}
                item_properties["rest_seconds"] = {"type": "null"}
                item_properties["group"] = {"type": "null"}
                item_properties["rest"] = {"$ref": "#/$defs/RestPrescription"}
                rest = definitions["RestPrescription"]["properties"]
                rest_kinds = {
                    "aerobic": "not_applicable",
                    "flexibility": "between_holds",
                    "balance": "between_attempts",
                    "functional": "between_tasks",
                }
                rest["kind"] = {
                    "type": "string",
                    "enum": sorted({rest_kinds[mode] for mode in modes}),
                }
                if modes == {"aerobic"}:
                    rest["seconds"] = {"type": "null"}
                elif "aerobic" not in modes:
                    rest["seconds"] = {"type": "integer", "minimum": 0}
                if "balance" in modes or "functional" in modes:
                    definitions["TaskDose"]["properties"]["kind"] = {
                        "type": "string",
                        "enum": sorted(modes & {"balance", "functional"}),
                    }
                if "aerobic" in modes:
                    definitions["AerobicDose"]["properties"]["observation_fact"] = {
                        "type": "string",
                        "enum": ["reported_talk_test"],
                    }
                    approved_intensities = sorted(
                        {
                            v
                            for rule in context.get("rules", {}).get("rules", [])
                            for v in rule.get("permitted_values", {}).get("aerobic_intensity", [])
                        }
                    )
                    if approved_intensities:
                        definitions["AerobicDose"]["properties"]["intensity"] = {
                            "type": "string",
                            "enum": approved_intensities,
                        }
            for key in (
                "policy_version",
                "dictionary_version",
                "accounting_method_version",
                "input_snapshot_sha256",
            ):
                if key in context:
                    schema["properties"][key] = {"type": "string", "enum": [context[key]]}
        dimensions = context.get("rule_dimensions", {})
        if dimensions:
            for dimension in get_args(Dimension):
                schema["$defs"]["TypedPrescriptionItem"]["properties"]["decision_rules"][
                    "properties"
                ][dimension] = {
                    "type": "string",
                    "enum": [key for key, value in dimensions.items() if value == dimension],
                }
        execution = context.get("rules", {})
        numeric_modes = sorted(
            {
                key
                for rule in execution.get("rules", [])
                for key in rule.get("bounds", {})
                if key in {"rir", "rpe", "percent_1rm", "external_load_kg"}
            }
        )
        if numeric_modes:
            definitions["NumericIntensity"]["properties"]["mode"] = {
                "type": "string",
                "enum": numeric_modes,
            }
        scales = sorted(
            {
                key
                for rule in execution.get("rules", [])
                for key in rule.get("permitted_scale_keys", [])
            }
        )
        if scales:
            definitions["NumericIntensity"]["properties"]["scale_key"] = {
                "type": "string",
                "enum": scales,
            }
        if "instructions" in execution:
            progression_choices = [
                definition
                for definition in execution["instructions"].values()
                if definition["kind"] == "progression"
            ]
            for field in ("condition_fact", "action_key", "unit"):
                values = sorted(
                    {
                        definition[field]
                        for definition in progression_choices
                        if definition.get(field) is not None
                    }
                )
                if values:
                    definitions["Progression"]["properties"][field] = {
                        "type": "string",
                        "enum": values,
                    }
            for model, field, kind in (
                ("InstructionIntensity", "instruction_key", "relative_load"),
                ("Progression", "instruction_key", "progression"),
                ("Progression", "stop_instruction_key", "stop"),
                ("Progression", "regression_instruction_key", "regression"),
            ):
                keys = [
                    key
                    for key, instruction in execution["instructions"].items()
                    if instruction["kind"] == kind
                ]
                if keys:
                    definitions[model]["properties"][field] = {"type": "string", "enum": keys}
                elif model == "InstructionIntensity":
                    # Remove an unavailable representation instead of emitting an
                    # empty enum that provider grammar compilers may reject.
                    intensity = definitions["TypedPrescriptionItem"]["properties"]
                    if intensity["intensity"] != {"type": "null"}:
                        intensity["intensity"] = {
                            "anyOf": [{"$ref": "#/$defs/NumericIntensity"}, {"type": "null"}]
                        }
            notes = [
                key
                for key, instruction in execution["instructions"].items()
                if instruction["kind"] == "note"
            ]
            definitions["TypedPrescriptionItem"]["properties"]["note_instruction_keys"]["items"] = (
                {"type": "string", "enum": notes} if notes else {"type": "string"}
            )
            if not notes:
                definitions["TypedPrescriptionItem"]["properties"]["note_instruction_keys"][
                    "maxItems"
                ] = 0
        calculations = execution.get("calculations", {})
        if not calculations:
            definitions["TypedPrescriptionItem"]["properties"]["calculated_load"] = {"type": "null"}
        else:
            definitions["CalculatedLoad"]["properties"]["calculation_id"] = {
                "type": "string",
                "enum": list(calculations),
            }

    def strict(node):
        if isinstance(node, list):
            for child in node:
                strict(child)
        elif isinstance(node, dict):
            node.pop("default", None)
            node.pop("discriminator", None)
            # These unions are disjoint because their kind/mode tags are constants.
            if "oneOf" in node:
                node["anyOf"] = node.pop("oneOf")
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for child in node.values():
                strict(child)

    strict(schema)
    # Providers receive only definitions reachable from this request's envelope.
    reachable = set()

    def references(node):
        if isinstance(node, list):
            for child in node:
                references(child)
        elif isinstance(node, dict):
            reference = node.get("$ref", "")
            if reference.startswith("#/$defs/"):
                key = reference.removeprefix("#/$defs/")
                if key not in reachable:
                    reachable.add(key)
                    references(schema["$defs"][key])
            for key, child in node.items():
                if key != "$defs":
                    references(child)

    references(schema)
    schema["$defs"] = {key: value for key, value in schema["$defs"].items() if key in reachable}
    return schema
