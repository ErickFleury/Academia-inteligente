"""Mode-specific validation and lossless projection, shared by all entry points."""

from collections import Counter

from app.modules.training.prescription_contract import PrescriptionRejection
from app.modules.training.prescription_math import hold_duration


def required_choice(rule, name, value):
    if value not in rule.permitted_values.get(name, []):
        raise PrescriptionRejection("insufficient_support", "modality_choice_outside_policy")


def instruction_text(execution, rule, key, kind):
    definition = execution.instructions.get(key)
    if key not in rule.permitted_instruction_keys or definition is None or definition.kind != kind:
        raise PrescriptionRejection("insufficient_support", "unknown_modality_instruction")
    return definition.text_pt_br


def validate_modality_item(item, rules, execution, snapshot, check):
    dose, volume, intensity = item.dose, rules["volume"], rules["intensity"]
    if item.mode == "aerobic":
        check(volume, "duration_minutes", dose.minutes)
        fact = snapshot.facts.get(dose.observation_fact)
        classification = {"talk_not_sing": "moderate", "few_words": "vigorous"}
        if dose.observation_fact != "reported_talk_test":
            raise PrescriptionRejection(
                "insufficient_support",
                "invalid_observation_reference",
                issues=[
                    {
                        "field": "dose.observation_fact",
                        "reason": "invalid_observation_reference",
                        "allowed": ["reported_talk_test"],
                    }
                ],
            )
        if fact is None or fact.value not in classification:
            raise PrescriptionRejection("missing_input", "aerobic_intensity_observation_required")
        if classification[fact.value] != dose.intensity:
            raise PrescriptionRejection(
                "insufficient_support",
                "modality_choice_outside_policy",
                issues=[
                    {
                        "field": "dose.intensity",
                        "reason": "observation_intensity_mismatch",
                        "expected": classification[fact.value],
                    }
                ],
            )
        required_choice(intensity, "aerobic_intensity", dose.intensity)
        return (
            "Moderada pelo teste da fala"
            if dose.intensity == "moderate"
            else "Vigorosa pelo teste da fala"
        )
    check(rules["rest"], item.rest.kind + ".seconds", item.rest.seconds)
    if item.mode == "flexibility":
        required_choice(rules["selection"], "targets", dose.target)
        required_choice(rules["selection"], "sides", dose.side)
        check(volume, "holds", dose.holds)
        check(volume, "hold_seconds", dose.hold_seconds)
        check(volume, "duration_seconds_per_side", hold_duration(dose.holds, dose.hold_seconds, 1))
    else:
        required_choice(rules["selection"], "sides", dose.side)
        check(volume, "attempts", dose.attempts)
        check(volume, dose.unit, dose.amount)
        if dose.completed is not None:
            observed = snapshot.facts.get("completed_attempts")
            if observed is None or observed.value != dose.completed:
                raise PrescriptionRejection(
                    "missing_input", "completed_attempts_observation_required"
                )
        instruction_text(execution, rules["restrictions"], dose.support_instruction_key, "note")
        instruction_text(execution, rules["restrictions"], dose.supervision_instruction_key, "note")
    return instruction_text(execution, intensity, dose.intensity_instruction_key, "relative_load")


def modality_dose_text(item):
    dose = item.dose
    sides = {
        "left": "lado esquerdo",
        "right": "lado direito",
        "each_side": "cada lado",
        "bilateral": "bilateral",
    }
    if item.mode == "aerobic":
        return f"{dose.minutes} min contínuos"
    if item.mode == "flexibility":
        return f"{dose.holds} × {dose.hold_seconds} s; {sides[dose.side]}"
    units = {"seconds": "s", "steps": "passos", "repetitions": "repetições"}
    return f"{dose.attempts} tentativas × {dose.amount} {units[dose.unit]}; {sides[dose.side]}"


def summarize_modes(candidate, vigorous_equivalence):
    occurrences = (
        Counter(o.session_id for o in candidate.schedule.occurrences)
        if candidate.schedule
        else None
    )
    sessions, weekly = {}, {}
    for session in candidate.sessions:
        entries = {}
        for item in session.items:
            if item.mode == "resistance":
                continue
            dose = item.dose
            entry = {
                "mode": item.mode,
                "exercise_key": item.exercise_key,
                "variation_key": item.variation_key,
            }
            if item.mode == "aerobic":
                entry.update(minutes=dose.minutes, intensity=dose.intensity)
                entry["moderate_equivalent_minutes"] = (
                    dose.minutes
                    if dose.intensity == "moderate"
                    else None
                    if vigorous_equivalence is None
                    else dose.minutes * vigorous_equivalence
                )
            elif item.mode == "flexibility":
                entry.update(
                    side=dose.side,
                    target=dose.target,
                    seconds_per_side=hold_duration(dose.holds, dose.hold_seconds, 1),
                )
            else:
                entry.update(
                    side=dose.side,
                    planned_attempts=dose.attempts,
                    observed_completed_attempts=dose.completed,
                    unit=dose.unit,
                    amount=dose.amount,
                )
            entries[item.item_id] = entry
            if occurrences is not None:
                count = occurrences[session.session_id]
                aggregate = {**entry, "occurrences": count}
                for name in (
                    "minutes",
                    "moderate_equivalent_minutes",
                    "seconds_per_side",
                    "planned_attempts",
                ):
                    if name in aggregate and aggregate[name] is not None:
                        aggregate[name] *= count
                if "observed_completed_attempts" in aggregate:
                    # A template observation is not proof of completion of future occurrences.
                    aggregate["observed_completed_attempts"] = None
                weekly[item.item_id] = aggregate
        sessions[session.session_id] = entries
    return {"sessions": sessions, "seven_day_totals": weekly if occurrences is not None else None}
