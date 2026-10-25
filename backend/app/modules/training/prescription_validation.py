"""Backend-owned validation; operational authorization stays in the runtime adapter."""

from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from app.modules.knowledge.acquisition import digest
from app.modules.knowledge.service import ALLOWED_LICENSES, MAX_CHUNKS, KnowledgeContext
from app.modules.training.prescription_accounting import (
    AccountingItem,
    AccountingMethod,
    RepetitionCount,
    summarize_development_workload,
)
from app.modules.training.prescription_contract import (
    DevelopmentExecutionContract,
    InputSnapshot,
    InstructionIntensity,
    PrescriptionRejection,
    Repetitions,
    TypedPrescription,
    fact_is_current,
    record_hash,
)
from app.modules.training.prescription_math import percentage_increase, percentage_load, round_load
from app.modules.training.prescription_mode_validation import (
    modality_dose_text,
    summarize_modes,
    validate_modality_item,
)
from app.modules.training.prescription_policy import DIMENSIONS, PolicyCatalog
from app.modules.training.schema import (
    KnowledgeCitation,
    TrainingPlanItemInput,
    TrainingPlanVersionInput,
)

VALIDATOR_VERSION = "prescription-remediation-2"
DECISION_LABELS = {
    "selection": "Escolha do exercício",
    "volume": "Séries e repetições",
    "intensity": "Carga e intensidade",
    "frequency": "Frequência e recuperação",
    "progression": "Progressão",
    "rest": "Descanso",
    "restrictions": "Adaptações às restrições",
}


def reject(reason, category="insufficient_support"):
    raise PrescriptionRejection(category, reason)


def _current_reference_source(source, client_id, today):
    try:
        return (
            source.get("client_id") in (None, str(client_id))
            and source.get("review_status") == "approved"
            and source.get("license") in ALLOWED_LICENSES
            and source.get("commercial_use_allowed") is True
            and isinstance(source.get("reviewed_by"), str)
            and bool(source["reviewed_by"].strip())
            and isinstance(source.get("url"), str)
            and source["url"].startswith("https://")
            and date.fromisoformat(source["reviewed_at"])
            <= today
            < date.fromisoformat(source["review_due_at"])
        )
    except (ValueError, KeyError, TypeError, AttributeError):
        return False


def _check_bound(rule, parameter, minimum, maximum=None):
    bound = rule.bounds.get(parameter)
    if bound is None:
        reject("missing_parameter_rule")
    maximum = minimum if maximum is None else maximum
    if minimum is None or maximum is None:
        reject("required_quantity_unknown", "missing_input")
    if not bound.contains(minimum) or not bound.contains(maximum):
        raise PrescriptionRejection(
            "insufficient_support",
            "parameter_outside_policy",
            issues=[
                {
                    "field": parameter,
                    "rule_id": rule.decision_id,
                    "reason": "parameter_outside_policy",
                    "allowed": bound.model_dump(mode="json"),
                }
            ],
        )


def _range_text(minimum, maximum):
    def number(value):
        return format(Decimal(value).normalize(), "f").replace(".", ",")

    return number(minimum) if minimum == maximum else f"{number(minimum)}–{number(maximum)}"


def validate_development_prescription(
    *,
    candidate: TypedPrescription | None,
    snapshot: InputSnapshot,
    catalog: PolicyCatalog,
    execution: DevelopmentExecutionContract,
    accounting: AccountingMethod,
    evidence: KnowledgeContext,
    source_catalog: dict,
    client_id,
    current_revision: int | None = None,
    now: datetime | None = None,
) -> dict:
    """Validate trusted backend context and return typed/projection/trace together.

    Approval-shaped fixture records are structural test inputs only. Calling this
    development helper cannot enable any real policy or production endpoint.
    """
    now = now or datetime.now(UTC)
    try:
        if candidate is not None:
            candidate = TypedPrescription.model_validate(candidate.model_dump())
        snapshot = InputSnapshot.model_validate(snapshot.model_dump())
        execution = DevelopmentExecutionContract.model_validate(execution.model_dump())
        catalog = PolicyCatalog.model_validate(catalog.model_dump())
        accounting = AccountingMethod.model_validate(accounting.model_dump())
    except ValidationError:
        reject("reviewed_contract_invalid_or_expired")
    if snapshot.client_id != client_id:
        reject("input_owner_mismatch")
    if candidate is not None and candidate.expected_revision != current_revision:
        reject("stale_revision")
    if candidate is not None and candidate.input_snapshot_sha256 != record_hash(snapshot):
        reject("input_snapshot_changed", "missing_input")
    if candidate is not None and candidate.schema_version != execution.schema_version:
        reject("prescription_schema_version_mismatch")
    policy = next((p for p in catalog.policies if p.id == execution.policy_id), None)
    if policy is None or policy.status != "approved" or policy.review_due_at <= now.date():
        reject("policy_not_current")
    if accounting.status != "approved" or accounting.review_due_at <= now.date():
        reject("accounting_not_current")
    if catalog.dictionary.status != "approved":
        reject("dictionary_not_approved")
    if (
        candidate is not None
        and (
            candidate.policy_version != policy.version
            or candidate.dictionary_version != catalog.dictionary.version
            or candidate.accounting_method_version != accounting.version
        )
        or policy.accounting_method_version != accounting.version
        or accounting.dictionary_version != catalog.dictionary.version
    ):
        reject("contract_version_changed")
    # Require every snapshot fact to have explicit authority and current confirmation.
    requirements = {requirement.key: requirement for requirement in execution.input_requirements}
    if len(requirements) != len(execution.input_requirements):
        reject("duplicate_input_requirement")
    if not {"training_goal", "training_experience"} <= requirements.keys():
        reject("required_input_contract_missing")
    if set(snapshot.facts) - requirements.keys():
        reject("unnecessary_snapshot_fact", "missing_input")
    for key, requirement in requirements.items():
        fact = snapshot.facts.get(key)
        if not requirement.collection_approved or not fact_is_current(fact, now):
            raise PrescriptionRejection(
                "missing_input"
                if requirement.missing_action == "clarify"
                else "insufficient_support",
                "required_input_missing_stale_or_conflicting",
                issues=[{"field": key, "reason": "required_input_missing_stale_or_conflicting"}],
            )
        if (
            requirement.max_age_seconds is not None
            and (now - fact.observed_at).total_seconds() > requirement.max_age_seconds
        ):
            reject("policy_input_validity_expired", "missing_input")
        if (
            policy.approval_basis == "owner_decision"
            and requirement.source == "request"
            and (not fact.source_actor_subject or not fact.confirmed_by_subject)
        ):
            reject("input_actor_provenance_required", "missing_input")
        if fact.source != requirement.source:
            reject("input_authority_mismatch", "missing_input")
        if (
            fact.source_actor_role not in requirement.allowed_actor_roles
            or fact.confirmed_by not in requirement.allowed_actor_roles
            or requirement.measurement_method is not None
            and fact.measurement_method != requirement.measurement_method
        ):
            reject("input_authority_mismatch", "missing_input")
        if requirement.expected_value is not None and (
            type(fact.value) is not type(requirement.expected_value)
            or fact.value != requirement.expected_value
        ):
            reject("unsupported_input_combination")
    goal = snapshot.facts["training_goal"].value
    if (
        not isinstance(goal, str)
        or goal.casefold() not in {value.casefold() for value in policy.exact_goal_mappings}
        or snapshot.facts["training_experience"].value not in policy.experience_levels
    ):
        reject("unknown_goal_or_experience")
    decisions = {d.id: d for d in policy.decisions}
    rules = {r.decision_id: r for r in execution.rules}
    if len(rules) != len(execution.rules) or set(rules) != set(decisions):
        reject("executable_rule_contract_incomplete")
    for conflict in execution.documented_conflicts:
        decision = decisions.get(conflict.decision_id)
        fact = snapshot.facts.get(conflict.fact_key)
        if decision is None or decision.dimension != "restrictions":
            reject("unreviewed_restriction_conflict")
        if fact is not None and fact.value == conflict.expected_value:
            raise PrescriptionRejection(
                "restriction_conflict", "documented_restriction_conflict", action=conflict.action
            )
    if evidence.knowledge_status == "unavailable":
        reject("retrieval_unavailable", "technical_unavailability")
    if evidence.knowledge_status == "outdated":
        reject("source_review_expired")
    if not evidence.chunks or len(evidence.chunks) > MAX_CHUNKS:
        reject("missing_or_excessive_evidence")
    if any(
        not isinstance(chunk, dict)
        or any(
            not isinstance(chunk.get(key), str)
            for key in ("chunk_id", "source_id", "content", "section")
        )
        for chunk in evidence.chunks
    ):
        reject("invalid_retrieved_passage")
    selected = {chunk["chunk_id"]: chunk for chunk in evidence.chunks}
    if len(selected) != len(evidence.chunks):
        reject("duplicate_retrieved_passage")
    if not isinstance(source_catalog, dict) or not isinstance(source_catalog.get("sources"), list):
        reject("invalid_source_catalog")
    entries = source_catalog["sources"]
    if any(not isinstance(s, dict) or not isinstance(s.get("id"), str) for s in entries):
        reject("invalid_source_catalog")
    sources = {source["id"]: source for source in entries}
    if len(sources) != len(entries):
        reject("duplicate_source_identity")
    proven = {}
    for decision in decisions.values():
        valid = []
        for reference in decision.evidence:
            retrieved = selected.get(reference.passage_id)
            source = sources.get(reference.source_id)
            if (
                not retrieved
                or not source
                or not _current_reference_source(source, client_id, now.date())
            ):
                continue
            if not isinstance(source.get("chunks"), list):
                continue
            provenance = source.get("provenance")
            if not isinstance(provenance, dict):
                continue
            chunk = next(
                (
                    c
                    for c in source["chunks"]
                    if isinstance(c, dict) and c.get("id") == reference.passage_id
                ),
                None,
            )
            if (
                not chunk
                or retrieved["source_id"] != source["id"]
                or retrieved["content"] != chunk.get("content")
                or retrieved["section"] != chunk.get("section")
                or reference.locator != chunk.get("section")
                or reference.passage_sha256 != digest(retrieved["content"].encode())
                or reference.artifact_sha256 != provenance.get("artifact_sha256")
            ):
                continue
            valid.append(reference.model_dump(mode="json"))
        if valid:
            proven[decision.id] = valid
    if {decisions[identifier].dimension for identifier in proven} != DIMENSIONS:
        reject("mandatory_rule_without_applicable_retrieved_source")
    if candidate is None:
        permitted = {reference["passage_id"] for refs in proven.values() for reference in refs}
        return {
            "purpose": execution.purpose + "_preflight",
            "policy_version": policy.version,
            "permitted_rule_ids": list(proven),
            "input_snapshot_sha256": record_hash(snapshot),
            "evidence": KnowledgeContext(
                tuple(chunk for chunk in evidence.chunks if chunk["chunk_id"] in permitted),
                evidence.knowledge_status,
                evidence.knowledge_limitations,
            ),
        }
    if candidate.schedule is not None and (
        snapshot.schedule is None
        or candidate.schedule != snapshot.schedule
        or snapshot.facts.get("schedule_confirmed") is None
        or snapshot.facts["schedule_confirmed"].value is not True
    ):
        reject("schedule_not_confirmed", "missing_input")
    dictionary = {e.key: e for e in catalog.dictionary.exercises}
    accounting_items, projection, trace, instructions = [], [], [], []
    for session in candidate.sessions:
        for item in session.items:

            def check_item_bound(*args):
                try:
                    return _check_bound(*args)
                except PrescriptionRejection as error:
                    for issue in error.issues:
                        issue.update(
                            session_id=session.session_id,
                            item_id=item.item_id,
                            position=len(projection) + 1,
                        )
                    raise

            exercise = dictionary.get(item.exercise_key)
            if exercise is None or item.variation_key not in exercise.variations:
                reject("unknown_exercise_or_variation")
            if item.mode not in exercise.dose_modes or item.mode not in accounting.supported_modes:
                reject("unsupported_prescription_mode")
            if exercise.equipment_constraints and item.equipment_model_id is None:
                reject("equipment_mapping_missing", "missing_input")
            if set(item.decision_rules) != DIMENSIONS:
                reject("mandatory_dimension_missing")
            item_rules = {}
            for dimension, identifier in item.decision_rules.items():
                decision = decisions.get(identifier)
                if decision is None or decision.dimension != dimension:
                    reject("invalid_decision_rule")
                if identifier not in proven:
                    reject("mandatory_rule_without_applicable_retrieved_source")
                item_rules[dimension] = rules[identifier]
                trace.append(
                    {
                        "path": f"{session.session_id}/{item.item_id}/{dimension}",
                        "label_pt_br": f"{exercise.label_pt_br} — {DECISION_LABELS[dimension]}",
                        "rule_id": identifier,
                        "evidence": proven[identifier],
                        "derivation": decision.derivation,
                    }
                )
            selection = item_rules["selection"]
            if item.variation_key not in selection.allowed_exercises.get(item.exercise_key, []):
                reject("exercise_outside_policy")
            if item.mode == "resistance":
                check_item_bound(item_rules["volume"], "sets", item.sets)
                check_item_bound(
                    item_rules["volume"], item.dose.kind, item.dose.minimum, item.dose.maximum
                )
                check_item_bound(
                    item_rules["rest"],
                    "rest_seconds" if item.group is None else item.group.rest.kind + ".seconds",
                    item.rest_seconds if item.group is None else item.group.rest.seconds,
                )
                intensity_rule = item_rules["intensity"]
                if isinstance(item.intensity, InstructionIntensity):
                    key = item.intensity.instruction_key
                    instruction = execution.instructions.get(key)
                    if (
                        key not in intensity_rule.permitted_instruction_keys
                        or instruction is None
                        or instruction.kind != "relative_load"
                    ):
                        reject("unknown_load_instruction")
                    load_text = instruction.text_pt_br
                else:
                    if item.intensity.scale_key not in intensity_rule.permitted_scale_keys:
                        reject("unknown_intensity_scale")
                    check_item_bound(
                        intensity_rule,
                        item.intensity.mode,
                        item.intensity.minimum,
                        item.intensity.maximum,
                    )
                    if (
                        item.intensity.baseline_fact
                        and item.intensity.baseline_fact not in snapshot.facts
                    ):
                        reject("measured_baseline_missing", "missing_input")
                    if (
                        item.intensity.mode in ("percent_1rm", "external_load_kg")
                        and item.intensity.baseline_fact != "baseline_capacity"
                    ):
                        reject("measured_baseline_invalid", "missing_input")
                    units = {
                        "rir": "RIR",
                        "rpe": "RPE",
                        "percent_1rm": "% de 1RM",
                        "external_load_kg": "kg",
                    }
                    amount_text = _range_text(item.intensity.minimum, item.intensity.maximum)
                    load_text = f"{amount_text} {units[item.intensity.mode]}"
                if (
                    candidate.schema_version == 2
                    and not isinstance(item.intensity, InstructionIntensity)
                    and item.intensity.mode in ("percent_1rm", "external_load_kg")
                    and item.calculated_load is None
                ):
                    reject("calculation_intent_required")
                if item.calculated_load is not None:
                    definition = execution.calculations.get(item.calculated_load.calculation_id)
                    if definition is None or (
                        definition.exercise_key,
                        definition.variation_key,
                    ) != (item.exercise_key, item.variation_key):
                        reject("unknown_load_calculation")
                    baseline = snapshot.facts.get(definition.baseline_fact)
                    method = (
                        "measured_1rm"
                        if definition.operation == "percentage_load"
                        else "observed_working_load"
                    )
                    if (
                        baseline is None
                        or not fact_is_current(baseline, now)
                        or (baseline.exercise_key, baseline.variation_key)
                        != (item.exercise_key, item.variation_key)
                        or baseline.measurement_unit != "kg"
                        or baseline.measurement_method != method
                        or baseline.measurement_convention != definition.load_convention
                    ):
                        reject("measured_baseline_invalid", "missing_input")
                    compute = (
                        percentage_load
                        if definition.operation == "percentage_load"
                        else percentage_increase
                    )
                    computed = compute(baseline.value, definition.percent)
                    if definition.increment_kg is not None:
                        computed = round_load(
                            computed, definition.increment_kg, definition.rounding
                        )
                    incompatible_intensity = not isinstance(
                        item.intensity, InstructionIntensity
                    ) and (
                        item.intensity.mode == "external_load_kg"
                        and (
                            item.intensity.minimum != computed or item.intensity.maximum != computed
                        )
                        or item.intensity.mode == "percent_1rm"
                        and (
                            definition.operation != "percentage_load"
                            or item.intensity.minimum != definition.percent
                            or item.intensity.maximum != definition.percent
                        )
                    )
                    if item.calculated_load.claimed_kg != computed or incompatible_intensity:
                        raise PrescriptionRejection(
                            "insufficient_support",
                            "calculated_quantity_mismatch",
                            issues=[
                                {
                                    "session_id": session.session_id,
                                    "item_id": item.item_id,
                                    "position": len(projection) + 1,
                                    "field": "calculated_load.claimed_kg",
                                    "reason": "calculated_quantity_mismatch",
                                    "expected": str(computed),
                                }
                            ],
                        )
                    check_item_bound(intensity_rule, "external_load_kg", computed)
                    load_text = f"{_range_text(computed, computed)} kg" + (
                        f"; {load_text}"
                        if not isinstance(item.intensity, InstructionIntensity)
                        and item.intensity.mode in ("rir", "rpe")
                        else ""
                    )
            else:
                load_text = validate_modality_item(
                    item, item_rules, execution, snapshot, check_item_bound
                )
            progression = item.progression
            progression_rule = item_rules["progression"]
            if (
                progression.condition_fact not in requirements
                or not requirements[progression.condition_fact].collection_approved
            ):
                reject("progression_condition_unavailable", "missing_input")
            for key, kind in (
                (progression.instruction_key, "progression"),
                (progression.stop_instruction_key, "stop"),
                (progression.regression_instruction_key, "regression"),
            ):
                definition = execution.instructions.get(key)
                if (
                    key not in progression_rule.permitted_instruction_keys
                    or definition is None
                    or definition.kind != kind
                ):
                    reject("unknown_progression_instruction")
            definition = execution.instructions[progression.instruction_key]
            if (
                definition.condition_fact != progression.condition_fact
                or definition.action_key != progression.action_key
                or definition.unit != progression.unit
                or definition.amount_bounds is None
                or not definition.amount_bounds.contains(progression.amount)
            ):
                reject("progression_outside_policy")
            note_text = []
            for key in item.note_instruction_keys:
                definition = execution.instructions.get(key)
                if (
                    definition is None
                    or definition.kind != "note"
                    or key not in item_rules["restrictions"].permitted_instruction_keys
                ):
                    reject("unapproved_prescriptive_note")
                note_text.append(definition.text_pt_br)
            instructions.append(
                {
                    "session_id": session.session_id,
                    "item_id": item.item_id,
                    "progression": execution.instructions[progression.instruction_key].text_pt_br,
                    "amount": str(progression.amount),
                    "unit": progression.unit,
                    "stop": execution.instructions[progression.stop_instruction_key].text_pt_br,
                    "regression": execution.instructions[
                        progression.regression_instruction_key
                    ].text_pt_br,
                    "notes": note_text,
                }
            )
            dose_text = (
                _range_text(item.dose.minimum, item.dose.maximum)
                if item.mode == "resistance"
                else modality_dose_text(item)
            )
            if item.mode == "resistance" and item.dose.kind == "duration_seconds":
                dose_text += " s"
            details = None
            if item.mode != "resistance" or item.group is not None:
                details = {
                    "mode": item.mode,
                    "dose": item.dose.model_dump(mode="json"),
                    "rest": item.rest.model_dump(mode="json") if item.rest else None,
                    "group": item.group.model_dump(mode="json") if item.group else None,
                }
            projection.append(
                TrainingPlanItemInput(
                    exercise_name=f"{exercise.label_pt_br} (Dia {session.label})",
                    sets=item.sets,
                    repetitions=dose_text,
                    load_guidance=load_text,
                    rest_seconds=item.rest_seconds
                    if item.mode == "resistance"
                    else item.rest.seconds,
                    dose_details=details,
                    equipment_model_id=item.equipment_model_id,
                )
            )
            if item.mode == "resistance":
                accounting_items.append(
                    AccountingItem(
                        item_id=item.item_id,
                        session_id=session.session_id,
                        exercise_key=item.exercise_key,
                        variation_key=item.variation_key,
                        sets=item.sets,
                        set_role="working",
                        repetitions=RepetitionCount(
                            minimum=item.dose.minimum, maximum=item.dose.maximum
                        )
                        if isinstance(item.dose, Repetitions)
                        else None,
                        repetition_convention="total",
                        external_load_kg=(
                            item.calculated_load.claimed_kg
                            if item.calculated_load is not None
                            else item.intensity.minimum
                            if not isinstance(item.intensity, InstructionIntensity)
                            and item.intensity.mode == "external_load_kg"
                            and item.intensity.minimum == item.intensity.maximum
                            else None
                        ),
                        load_convention=execution.calculations[
                            item.calculated_load.calculation_id
                        ].load_convention
                        if item.calculated_load is not None
                        else "unknown",
                    )
                )
    try:
        resistance_sessions = {item.session_id for item in accounting_items}
        resistance_schedule = (
            candidate.schedule.model_copy(
                update={
                    "occurrences": [
                        o
                        for o in candidate.schedule.occurrences
                        if o.session_id in resistance_sessions
                    ]
                }
            )
            if candidate.schedule is not None and accounting_items
            else None
        )
        totals = (
            summarize_development_workload(
                items=accounting_items,
                dictionary=catalog.dictionary,
                method=accounting,
                schedule=resistance_schedule,
            )
            if accounting_items
            else {
                "sessions": {},
                "seven_day_totals": {"session_occurrences": len(candidate.schedule.occurrences)}
                if candidate.schedule
                else None,
            }
        )
    except ValueError:
        reject("accounting_contract_mismatch")
    if candidate.scope == "plan_revision" and totals["seven_day_totals"] is None:
        reject("weekly_schedule_missing", "missing_input")
    mode_totals = summarize_modes(candidate, execution.vigorous_equivalence)
    for session in candidate.sessions:
        total = totals["sessions"].get(session.session_id)
        if total is not None and total["muscles"] is None:
            reject("muscle_accounting_unknown")
        for item in session.items:
            volume_rule = rules[item.decision_rules["volume"]]
            frequency_rule = rules[item.decision_rules["frequency"]]
            if item.mode != "resistance":
                weekly = mode_totals["seven_day_totals"]
                if (
                    frequency_rule.requires_weekly_context
                    or candidate.scope == "plan_revision"
                    or any(k.startswith("weekly_") for k in volume_rule.bounds)
                ):
                    if weekly is None:
                        reject("weekly_schedule_missing", "missing_input")
                if weekly is not None:
                    from collections import Counter

                    occurrence_count = Counter(
                        o.session_id for o in candidate.schedule.occurrences
                    )[session.session_id]
                    _check_bound(frequency_rule, "sessions_per_seven_days", occurrence_count)
                    for parameter in volume_rule.bounds:
                        if parameter.startswith("weekly_"):
                            quantity = weekly[item.item_id].get(parameter[7:])
                            _check_bound(volume_rule, parameter, quantity)
                continue
            _check_bound(volume_rule, "session_working_sets", total["working_sets"])
            weekly = totals["seven_day_totals"]
            weekly_required = (
                frequency_rule.requires_weekly_context
                or candidate.scope == "plan_revision"
                or any(name.startswith("weekly_") for name in volume_rule.bounds)
                or "sessions_per_seven_days" in frequency_rule.bounds
            )
            if weekly_required and weekly is None:
                reject("weekly_schedule_missing", "missing_input")
            if weekly is not None:
                _check_bound(
                    frequency_rule, "sessions_per_seven_days", weekly["session_occurrences"]
                )
                _check_bound(volume_rule, "weekly_working_sets", weekly["working_sets"])
                if weekly["muscles"] is None:
                    reject("muscle_accounting_unknown")
                for muscle, values in weekly["muscles"].items():
                    for field in ("direct_sets", "indirect_sets"):
                        _check_bound(volume_rule, f"weekly_{field}.{muscle}", values[field])
                    weighted = f"weekly_weighted_sets.{muscle}"
                    if weighted in volume_rule.bounds:
                        _check_bound(volume_rule, weighted, values["weighted_sets"])
    projected = TrainingPlanVersionInput(
        name="Proposta de treino", objective=goal, items=projection
    )
    cited_ids = list(
        dict.fromkeys(
            reference["passage_id"] for references in proven.values() for reference in references
        )
    )
    knowledge = evidence.resolve_citations(cited_ids)
    return {
        "prescription_eligibility": "eligible",
        "purpose": execution.purpose,
        "validator_version": VALIDATOR_VERSION,
        "writer_configuration_sha256": execution.writer_configuration_sha256,
        "policy_version": policy.version,
        "policy_sha256": record_hash(catalog),
        "execution_sha256": record_hash(execution),
        "accounting_sha256": record_hash(accounting),
        "input_snapshot_sha256": record_hash(snapshot),
        "typed_content_sha256": record_hash(candidate),
        "input_snapshot": snapshot.model_dump(mode="json"),
        "rendered_content_sha256": record_hash(projected),
        "display_sha256": record_hash(
            {
                "projection": projected.model_dump(mode="json"),
                "instructions": instructions,
            }
        ),
        "evaluated_revision": current_revision,
        "scope": candidate.scope,
        "trace": trace,
        "totals": TypeAdapter(dict).dump_python(totals, mode="json"),
        "modality_totals": TypeAdapter(dict).dump_python(mode_totals, mode="json"),
        "typed_content": candidate.model_dump(mode="json"),
        "projection": projected.model_dump(mode="json"),
        "instructions": instructions,
        "citations": [
            KnowledgeCitation.model_validate(c).model_dump(mode="json") for c in knowledge.citations
        ],
        "knowledge_status": knowledge.knowledge_status,
        "knowledge_limitations": knowledge.knowledge_limitations,
        "approval_basis": policy.approval_basis,
        "professional_review_performed": policy.approval_basis == "independent_review",
    }
