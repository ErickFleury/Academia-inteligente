"""Authoritative unit-aware arithmetic; no inference of dose or measurements."""

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal


def quantity(value):
    if value is None or isinstance(value, bool):
        raise ValueError("quantity_unknown_or_invalid")
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("quantity_unknown_or_invalid")
    return result


def percentage_load(baseline, percent):
    return quantity(baseline) * quantity(percent) / Decimal(100)


def percentage_increase(current, percent):
    return quantity(current) + percentage_load(current, percent)


def round_load(value, increment, mode):
    step = quantity(increment)
    modes = {"floor": ROUND_FLOOR, "ceiling": ROUND_CEILING, "nearest": ROUND_HALF_UP}
    if not step or mode not in modes:
        raise ValueError("rounding_policy_required")
    return (quantity(value) / step).quantize(Decimal(1), rounding=modes[mode]) * step


def aerobic_equivalent(segments, vigorous_factor):
    """Segments are disjoint, observed minutes; unclassified time stays separate."""
    factor = quantity(vigorous_factor)
    if factor == 0:
        raise ValueError("equivalence_policy_required")
    total, unclassified, seen = Decimal(0), Decimal(0), {}
    for segment in segments:
        occurrence = segment["occurrence_id"]
        start, end = quantity(segment["start_minutes"]), quantity(segment["end_minutes"])
        if end <= start:
            raise ValueError("invalid_segment_interval")
        if any(start < b and end > a for a, b in seen.get(occurrence, [])):
            raise ValueError("overlapping_aerobic_segments")
        seen.setdefault(occurrence, []).append((start, end))
        intensity = segment["intensity"]
        if intensity == "moderate":
            total += end - start
        elif intensity == "vigorous":
            total += (end - start) * factor
        elif intensity == "unclassified":
            unclassified += end - start
        else:
            raise ValueError("unknown_aerobic_intensity")
    return {"moderate_equivalent_minutes": total, "unclassified_minutes": unclassified}


def hold_duration(holds, seconds, occurrences):
    for value in (holds, occurrences):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("positive_count_required")
    return quantity(seconds) * holds * occurrences


def scheduled_duration(durations, selected_occurrence, increment):
    if selected_occurrence not in durations:
        raise ValueError("unknown_schedule_occurrence")
    return sum((quantity(v) for v in durations.values()), Decimal(0)) + quantity(increment)
