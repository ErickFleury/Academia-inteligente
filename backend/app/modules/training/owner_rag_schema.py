"""Bound the assisted writer's identities/representation, without inventing doses."""

import json
import re
import unicodedata
from copy import deepcopy
from itertools import product
from pathlib import Path

from pydantic import ValidationError

from app.modules.training.prescription_contract import PrescriptionRejection, record_hash

DICTIONARY_PATH = Path(__file__).with_name("owner-rag-exercises.json")


def fold(value):
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(c)
        ).split()
    )


def dictionary():
    from app.modules.training.completeness import FULL_BODY_PATTERNS
    from app.modules.training.owner_rag_load import LOAD_GUIDANCE

    data = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    keys, aliases = set(), set()
    for item in data["exercises"]:
        if item.get("mode") not in {"resistance", "flexibility"}:
            raise ValueError("unknown_owner_exercise_mode")
        if not item.get("movement_patterns") or set(item["movement_patterns"]) - {
            *FULL_BODY_PATTERNS,
            "upper_accessory",
            "lower_accessory",
            "flexibility_upper",
            "flexibility_lower",
            "flexibility_trunk",
        }:
            raise ValueError("unknown_owner_movement_pattern")
        if item.get("load_capability") not in LOAD_GUIDANCE:
            raise ValueError("unknown_owner_load_capability")
        if not item["key"] or item["key"] in keys:
            raise ValueError("duplicate_owner_exercise_key")
        keys.add(item["key"])
        for name in (item["label_pt_br"], *item["aliases"]):
            if fold(name) in aliases:
                raise ValueError("ambiguous_owner_exercise_alias")
            aliases.add(fold(name))
    return data


def scoped_dictionary(focus, *, mode="resistance"):
    data = dictionary()
    data = {
        **data,
        "exercises": [e for e in data["exercises"] if e.get("mode", "resistance") == mode],
    }
    if focus and focus.get("scope") == "targeted":
        requested = {fold(group) for group in focus.get("muscle_groups", [])}
        items = [e for e in data["exercises"] if requested & {fold(group) for group in e["groups"]}]
        covered = {fold(group) for e in items for group in e["groups"]}
        if not items or not requested <= covered:
            raise PrescriptionRejection("insufficient_support", "unsupported_target_focus")
        data = {**data, "exercises": items}
    return data


def wire_names(context):
    labels = (
        context.get("owner_exercise_labels")
        or context.get("training_schedule", {}).get("session_labels", [])
        or ["A"]
    )
    if context.get("owner_preserve_unlabeled"):
        return [item["key"] for item in context["owner_exercise_dictionary"]["exercises"]]
    return [
        f"{item['key']} (Dia {label})"
        for label in labels
        for item in context["owner_exercise_dictionary"]["exercises"]
    ]


def exercise_for_name(value, context):
    name = re.sub(r"\s*\(Dia [A-G]\)\s*$", "", value)
    return next(
        (
            item
            for item in context["owner_exercise_dictionary"]["exercises"]
            if fold(name)
            in {fold(alias) for alias in (item["key"], item["label_pt_br"], *item["aliases"])}
        ),
        None,
    )


def constrain_item(schema, context):
    from app.modules.training.owner_rag_load import LOAD_GUIDANCE

    if "anyOf" in schema:
        for child in schema["anyOf"]:
            constrain_item(child, context)
        return
    from app.modules.training.owner_rag_flexibility import is_flexibility

    if is_flexibility(context):
        from app.modules.training.owner_rag_flexibility import constrain_item as flexibility_schema

        flexibility_schema(schema, context)
        return
    schema["properties"]["exercise_name"] = {"type": "string", "enum": wire_names(context)}
    schema["properties"]["repetitions"] = {
        "type": "string",
        # Preserve every valid positive range; domain validation compares all bounds.
        "pattern": "^(?:[1-9][0-9]*|"
        + "|".join(f"{n}-(?:[{n}-9]|[1-9][0-9]+)" for n in range(1, 10))
        + "|[1-9][0-9]+-[1-9][0-9]+)$",
        "maxLength": 100,
    }
    if "load_guidance" in schema["properties"]:
        schema["properties"]["load_guidance"] = {
            "type": "string",
            "enum": sorted(
                {
                    LOAD_GUIDANCE[e["load_capability"]]
                    for e in context["owner_exercise_dictionary"]["exercises"]
                }
            ),
        }
    for field in ("equipment_requirement", "equipment_model_id"):
        if field in schema["properties"]:
            schema["properties"][field] = {"type": "null"}


def constrain_writer_schema(schema, context):
    if isinstance(schema, list):
        for child in schema:
            constrain_writer_schema(child, context)
    elif isinstance(schema, dict):
        properties = schema.get("properties", {})
        if "exercise_name" in properties and "repetitions" in properties:
            constrain_item(schema, context)
        if {"name", "objective", "items"} <= properties.keys() and context.get(
            "effective_training_goal"
        ):
            properties["objective"] = {
                "type": "string",
                "enum": [context["effective_training_goal"]],
            }
            from app.modules.training.owner_rag_flexibility import is_flexibility

            if is_flexibility(context):
                properties["name"] = {"type": "string", "enum": ["Flexibilidade"]}
        for child in schema.values():
            constrain_writer_schema(child, context)


def constrain_session_schema(schema, context, *, definitions=None):
    """Closed, requested day containers prevent an A-only multi-day wire response."""
    labels = context.get("training_schedule", {}).get("session_labels", [])
    full_body = (context.get("training_focus") or {}).get("scope") == "full_body"
    if len(labels) < 2 and not full_body:
        return
    labels = labels or ["A"]
    if definitions is None:
        definitions = schema.setdefault("$defs", {})
    if isinstance(schema, list):
        for child in schema:
            constrain_session_schema(child, context, definitions=definitions)
    elif isinstance(schema, dict):
        for child in list(schema.values()):
            if child is not definitions:
                constrain_session_schema(child, context, definitions=definitions)
        properties = schema.get("properties", {})
        if {"name", "objective", "items"} <= properties.keys():
            original = properties.pop("items")
            sessions = {}
            for label in labels:
                day = deepcopy(original)
                day["minItems"] = 1
                day["maxItems"] = len(context["owner_exercise_dictionary"]["exercises"])
                constrain_item(
                    day["items"],
                    {
                        **context,
                        "owner_exercise_labels": [label],
                        "owner_preserve_unlabeled": False,
                    },
                )
                if full_body:
                    from app.modules.training.completeness import full_body_patterns

                    slots = {}
                    patterns = full_body_patterns(context)
                    for pattern in (*patterns, "accessories"):
                        matching = [
                            e
                            for e in context["owner_exercise_dictionary"]["exercises"]
                            if (
                                pattern in e["movement_patterns"]
                                if pattern != "accessories"
                                else not set(e["movement_patterns"]) & set(patterns)
                            )
                        ]
                        slot = deepcopy(day)
                        slot["minItems"] = 0 if pattern == "accessories" else 1
                        slot["maxItems"] = len(matching)
                        if not matching and pattern != "accessories":
                            raise PrescriptionRejection(
                                "insufficient_support", "unsupported_full_body_dictionary"
                            )
                        if not matching:
                            slot["items"] = {"type": "null"}
                            slots[pattern] = slot
                            continue
                        constrain_item(
                            slot["items"],
                            {
                                **context,
                                "owner_exercise_labels": [label],
                                "owner_preserve_unlabeled": False,
                                "owner_exercise_dictionary": {
                                    **context["owner_exercise_dictionary"],
                                    "exercises": matching,
                                },
                            },
                        )
                        definition = "OwnerRagSlot_" + pattern
                        slot["items"]["properties"]["exercise_name"] = {
                            "type": "string",
                            "enum": [e["key"] for e in matching],
                        }
                        definitions[definition] = slot["items"]
                        slot["items"] = {"$ref": "#/$defs/" + definition}
                        slots[pattern] = slot
                    sessions[label] = {
                        "type": "object",
                        "properties": slots,
                        "required": list(slots),
                        "additionalProperties": False,
                    }
                else:
                    sessions[label] = day
            properties["sessions"] = {
                "type": "object",
                "properties": sessions,
                "required": labels,
                "additionalProperties": False,
            }
            schema["required"] = [key for key in schema.get("required", []) if key != "items"] + [
                "sessions"
            ]


def materialize_sessions(plan, context):
    if "sessions" not in plan:
        return plan
    expected = context.get("training_schedule", {}).get("session_labels", [])
    if not expected and (context.get("training_focus") or {}).get("scope") == "full_body":
        expected = ["A"]
    sessions = plan["sessions"]
    if (
        not expected
        or not isinstance(sessions, dict)
        or set(sessions) != set(expected)
        or "items" in plan
    ):
        raise PrescriptionRejection(
            "insufficient_support",
            "invalid_typed_candidate",
            issues=[
                {
                    "field": "session_labels",
                    "reason": "requested_sessions_required",
                    "allowed": expected,
                }
            ],
        )
    result = []
    for label in expected:
        if (
            isinstance(sessions[label], dict)
            and (context.get("training_focus") or {}).get("scope") == "full_body"
        ):
            from app.modules.training.completeness import full_body_patterns

            patterns = full_body_patterns(context)
            if set(sessions[label]) != {*patterns, "accessories"} or not all(
                isinstance(v, list) for v in sessions[label].values()
            ):
                raise PrescriptionRejection("insufficient_support", "invalid_typed_candidate")
            for pattern, rows in sessions[label].items():
                for row in rows:
                    exercise = (
                        exercise_for_name(row.get("exercise_name", ""), context)
                        if isinstance(row, dict)
                        else None
                    )
                    if exercise is None or (
                        pattern != "accessories" and pattern not in exercise["movement_patterns"]
                    ):
                        raise PrescriptionRejection(
                            "insufficient_support",
                            "invalid_typed_candidate",
                            issues=[
                                {
                                    "label": label,
                                    "field": "exercise_name",
                                    "reason": "movement_pattern_mismatch",
                                    "pattern": pattern,
                                }
                            ],
                        )
            sessions = {
                **sessions,
                label: [
                    item for key in (*patterns, "accessories") for item in sessions[label][key]
                ],
            }
        if not isinstance(sessions[label], list) or not sessions[label]:
            raise PrescriptionRejection(
                "insufficient_support",
                "invalid_typed_candidate",
                issues=[
                    {
                        "field": "sessions",
                        "reason": "nonempty_requested_session_required",
                        "label": label,
                    }
                ],
            )
        for item in sessions[label]:
            if not isinstance(item, dict) or not isinstance(item.get("exercise_name"), str):
                raise PrescriptionRejection(
                    "insufficient_support",
                    "invalid_typed_candidate",
                    issues=[
                        {
                            "field": "exercise_name",
                            "reason": "recognized_exercise_required",
                            "label": label,
                        }
                    ],
                )
            value = item["exercise_name"]
            suffix = re.search(r"\s*\(Dia ([A-G])\)\s*$", value)
            if suffix and suffix.group(1) != label:
                raise PrescriptionRejection(
                    "insufficient_support",
                    "invalid_typed_candidate",
                    issues=[
                        {
                            "field": "exercise_name",
                            "reason": "session_container_mismatch",
                            "label": label,
                        }
                    ],
                )
            result.append({**item, "exercise_name": value if suffix else f"{value} (Dia {label})"})
    return {**{key: value for key, value in plan.items() if key != "sessions"}, "items": result}


def constrain_session_variation(schema, context):
    """Let the writer choose which prior movement to omit, never a fixed routine.

    Each branch omits at least one identity from every previous selection. This
    prevents copied sets even when the local model ignores correction prose.
    Empty movement slots invalidate a branch, preserving full-body coverage.
    Domain review remains authoritative, including the grounded repeat exception
    when this dictionary cannot express a distinct complete selection.
    """
    previous = [
        set(keys) - {None}
        for keys in context.get("previous_session_exercise_keys", {}).values()
        if keys
    ]
    if not previous:
        return
    exclusions = {frozenset(keys) for keys in product(*(sorted(keys) for keys in previous))}
    exclusions = sorted(
        (keys for keys in exclusions if not any(other < keys for other in exclusions)),
        key=lambda keys: (len(keys), sorted(keys)),
    )
    definitions = schema.get("$defs", {})

    def filtered(node, excluded):
        if isinstance(node, list):
            return [filtered(child, excluded) for child in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            node = definitions[node["$ref"].rsplit("/", 1)[-1]]
        result = {key: filtered(value, excluded) for key, value in node.items()}
        names = result.get("properties", {}).get("exercise_name")
        if names and "enum" in names:
            names["enum"] = [
                name
                for name in names["enum"]
                if re.sub(r"\s*\(Dia [A-G]\)\s*$", "", name) not in excluded
            ]
            if not names["enum"]:
                raise ValueError("empty_variation_slot")
        return result

    def visit(node):
        if isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            properties = node.get("properties", {})
            if {"name", "objective"} <= properties.keys() and (
                "items" in properties or "sessions" in properties
            ):
                branches = []
                for excluded in exclusions:
                    try:
                        branches.append(filtered(node, excluded))
                    except ValueError:
                        continue
                if branches:
                    node.clear()
                    node["anyOf"] = branches
                return
            for key, child in list(node.items()):
                if key != "$defs":
                    visit(child)

    visit(schema)


def constrain_review_schema(schema, context):
    labels = context.get("training_schedule", {}).get("session_labels", [])
    if not labels:
        return
    definitions = schema["$defs"]
    sessions = {}
    from app.modules.training.completeness import split_training_day

    for label in labels:
        session = deepcopy(definitions["AiTrainingSessionAssessment"])
        session["properties"]["label"] = {"type": "string", "enum": [label]}
        detail = deepcopy(definitions["AiTrainingItemAssessment"])
        detail["properties"]["position"] = {
            "type": "integer",
            "enum": [
                position
                for position, item in enumerate(context["proposed_plan"]["items"], 1)
                if split_training_day(item["exercise_name"])[0] == label
            ],
        }
        day_items = [
            item
            for item in context["proposed_plan"]["items"]
            if split_training_day(item["exercise_name"])[0] == label
        ]
        if day_items and all(
            exercise_for_name(item["exercise_name"], context) is not None for item in day_items
        ):
            # Identity has already passed deterministic dictionary validation.
            # Substantive restriction and coverage failures remain reviewable.
            detail["properties"]["reason"] = {
                "type": "string",
                "enum": ["restriction_not_respected"],
            }
            choices = session["properties"]["issues"]["items"]["enum"]
            session["properties"]["issues"]["items"]["enum"] = [
                reason for reason in choices if reason != "ambiguous_exercise"
            ]
        from app.modules.training.owner_rag_flexibility import is_flexibility

        if is_flexibility(context):
            choices = session["properties"]["issues"]["items"]["enum"]
            session["properties"]["issues"]["items"]["enum"] = [
                reason
                for reason in choices
                if reason in {"missing_session", "ambiguous_exercise", "restriction_not_respected"}
            ]
        session["properties"]["item_issues"]["items"] = detail
        passed = deepcopy(session)
        passed["properties"]["complete"] = {"type": "boolean", "enum": [True]}
        passed["properties"]["issues"]["maxItems"] = 0
        passed["properties"]["item_issues"]["maxItems"] = 0
        session["properties"]["complete"] = {"type": "boolean", "enum": [False]}
        sessions[label] = {"anyOf": [passed, session]}
    schema["properties"]["sessions"] = {
        "type": "object",
        "properties": sessions,
        "required": labels,
        "additionalProperties": False,
    }


def materialize_review(payload, context):
    if not isinstance(payload, dict):
        return payload
    sessions = payload.get("sessions")
    labels = context.get("training_schedule", {}).get("session_labels", [])
    if (
        isinstance(sessions, dict)
        and set(sessions) == set(labels)
        and all(
            isinstance(sessions[label], dict) and sessions[label].get("label") == label
            for label in labels
        )
    ):
        return {**payload, "sessions": [sessions[label] for label in labels]}
    return payload


def resolve_plan(plan, context):
    if "owner_exercise_dictionary" not in context:
        return plan
    plan = materialize_sessions(plan, context)
    items = context["owner_exercise_dictionary"]["exercises"]
    lookup = {
        fold(name): item
        for item in items
        for name in (item["key"], item["label_pt_br"], *item["aliases"])
    }
    labels = (
        context.get("owner_exercise_labels")
        or context.get("training_schedule", {}).get("session_labels", [])
        or ["A"]
    )
    if context.get("owner_preserve_unlabeled"):
        labels = [""]
    result = []
    for position, row in enumerate(plan["items"], 1):
        value = row["exercise_name"]
        suffix = re.search(r"\s*\(Dia ([A-G])\)\s*$", value)
        label = suffix.group(1) if suffix else labels[0] if len(labels) == 1 else None
        name = value[: suffix.start()] if suffix else value
        exercise = lookup.get(fold(name))
        if exercise is None or label not in labels:
            raise PrescriptionRejection(
                "insufficient_support",
                "unknown_exercise_or_variation",
                issues=[
                    {
                        "position": position,
                        "field": "exercise_name",
                        "reason": "unknown_exercise_or_variation",
                        "allowed": wire_names(context),
                    }
                ],
            )
        from app.modules.training.owner_rag_flexibility import is_flexibility, materialize_item

        if is_flexibility(context):
            try:
                row = materialize_item(row, exercise)
            except ValidationError as error:
                raise PrescriptionRejection(
                    "insufficient_support",
                    "invalid_typed_candidate",
                    issues=[
                        {
                            "position": position,
                            "field": str(e["loc"][0]),
                            "reason": "invalid_flexibility_quantity_or_side",
                        }
                        for e in error.errors(include_input=False)
                    ],
                ) from None
            result.append(
                {
                    **row,
                    "exercise_name": f"{exercise['label_pt_br']} (Dia {label})"
                    if label
                    else exercise["label_pt_br"],
                }
            )
            continue
        repetitions = row["repetitions"].replace("–", "-")
        if not re.fullmatch(r"[1-9][0-9]*(?:-[1-9][0-9]*)?", repetitions):
            raise PrescriptionRejection(
                "insufficient_support",
                "invalid_typed_candidate",
                issues=[
                    {
                        "position": position,
                        "field": "repetitions",
                        "reason": "numeric_repetition_range_required",
                    }
                ],
            )
        parts = [int(number) for number in repetitions.split("-")]
        if len(parts) == 2 and parts[0] > parts[1]:
            raise PrescriptionRejection(
                "insufficient_support",
                "invalid_typed_candidate",
                issues=[
                    {
                        "position": position,
                        "field": "repetitions",
                        "reason": "ordered_repetition_range_required",
                    }
                ],
            )
        result.append(
            {
                **row,
                "exercise_name": f"{exercise['label_pt_br']} (Dia {label})"
                if label
                else exercise["label_pt_br"],
                "repetitions": repetitions,
            }
        )
    from app.modules.training.owner_rag_flexibility import is_flexibility

    # Canonical presentation metadata, just like the Portuguese exercise labels.
    # No writer-selected duration, side, recovery or clinical fact is replaced.
    return {
        **plan,
        "items": result,
        **({"name": "Flexibilidade"} if is_flexibility(context) else {}),
    }


def dictionary_hash():
    return record_hash(dictionary())
