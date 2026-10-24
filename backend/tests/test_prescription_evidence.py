"""A positive model verdict cannot invent prescriptions missing from citations."""

from app.modules.knowledge.prescription_evidence import (
    allocation_options,
    prescription_gaps,
    source_parameters,
)


def item(**changes):
    return {
        "exercise_name": "Agachamento",
        "sets": 2,
        "repetitions": "8",
        "rest_seconds": 90,
        "load_guidance": "Peso corporal",
        **changes,
    }


def refs(text):
    return [{"passage_id": "R1", "content": text}]


def test_explicit_portuguese_and_english_doses_are_recognized():
    for source in [
        "Agachamento: 2 séries de 8 repetições, descanso de 90 segundos.",
        "Squat: two sets of eight repetitions; 90 seconds rest between sets.",
    ]:
        assert prescription_gaps([item()], refs(source), context={}) == []


def test_programming_quantities_and_named_technique_can_supply_complementary_evidence():
    sources = [
        {
            "passage_id": "R1",
            "content": "For resistance exercises: 2 sets of 8 repetitions, "
            "rest 90 seconds between sets.",
        },
        {
            "passage_id": "R2",
            "content": "Seção: Squat\nStarting Position: stand upright. "
            "Downward Movement: bend the knees.",
        },
    ]
    assert prescription_gaps([item()], sources, context={}) == []
    assert "exercise_supported" in prescription_gaps([item()], sources[:1], context={})[0]["fields"]
    assert "sets_supported" in prescription_gaps([item()], sources[1:], context={})[0]["fields"]
    assert (
        "rest_supported"
        in prescription_gaps([item(rest_seconds=60)], sources, context={})[0]["fields"]
    )


def test_guideline_ranges_support_values_inside_but_not_outside_them():
    source = refs("Squat: one to four sets, eight to twenty repetitions, 2–3 min rest.")
    assert (
        prescription_gaps([item(sets=3, repetitions="12-15", rest_seconds=120)], source, context={})
        == []
    )
    gaps = prescription_gaps([item(sets=5, repetitions="25", rest_seconds=60)], source, context={})
    assert set(gaps[0]["fields"]) == {"sets_supported", "repetitions_supported", "rest_supported"}


def test_general_activity_guidance_cannot_support_invented_resistance_doses():
    source = refs(
        "Adultos devem praticar 150 minutos de atividade física por semana. "
        "Inclua fortalecimento em 2 dias na semana."
    )
    gaps = prescription_gaps(
        [item(sets=3, repetitions="12-15", rest_seconds=60)], source, context={}
    )
    assert set(gaps[0]["fields"]) == {
        "exercise_supported",
        "sets_supported",
        "repetitions_supported",
        "rest_supported",
    }


def test_weekly_allocation_requires_exact_arithmetic_and_visible_explanation():
    source = refs(
        "Você pode caminhar. Faça 150 minutos de atividade física moderada por semana. "
        "Você pode dividir a prática em blocos de tempo."
    )
    context = {
        "client_answers": {"weekly_availability": {"value": 3}, "session_duration": {"value": 60}}
    }
    walking = item(
        exercise_name="Caminhada",
        sets=1,
        repetitions="50 minutos",
        rest_seconds=0,
        load_guidance="Intensidade moderada.",
    )
    objective = "150 minutos por semana em 3 dias de 50 minutos."
    assert prescription_gaps([walking], source, context=context, objective=objective) == []
    assert prescription_gaps([walking], source, context=context)
    walking["repetitions"] = "30-45 minutos"
    assert prescription_gaps([walking], source, context=context, objective=objective)
    walking["repetitions"] = "50 minutos"
    context["client_answers"]["session_duration"]["value"] = 30
    assert prescription_gaps([walking], source, context=context, objective=objective)


def test_rest_durations_are_not_continuous_activity_doses():
    source = refs("Caminhada. Agachamento: 2 séries de 8 repetições; descanso de 90 segundos.")
    walking = item(exercise_name="Caminhada", sets=1, repetitions="90 segundos", rest_seconds=0)
    assert prescription_gaps([walking], source, context={})[0]["fields"] == [
        "repetitions_supported"
    ]


def test_source_parameters_keep_provenance_and_units_for_generation():
    extracted = source_parameters(refs("Squat: 2 sets of 8 repetitions; rest 90 seconds."))
    assert extracted[0]["passage_id"] == "R1"
    assert extracted[0]["sets"] == [(2, 2)]
    assert extracted[0]["rest_seconds"] == [(90, 90)]
    assert "agachamento" in extracted[0]["named_activities"]


def test_source_allocation_is_exposed_in_minutes_without_new_prescription_rules():
    source = refs("Você pode caminhar. Faça 150 minutos por semana. Pode dividir a prática.")
    row = source_parameters(source, days_per_week=3)[0]
    assert row["weekly_minutes"] == [[150, 150]]
    assert row["daily_minutes_if_divided"] == [[50, 50]]
    assert "daily_minutes_if_divided" not in source_parameters(source)[0]


def test_unchanged_draft_values_use_the_record_but_new_doses_need_sources():
    previous = item()
    context = {"editable_training_draft": {"items": [previous]}}
    assert prescription_gaps([previous], [], context=context) == []
    gaps = prescription_gaps([item(rest_seconds=120)], [], context=context)
    assert gaps[0]["fields"] == ["rest_supported"]
    gaps = prescription_gaps([item(exercise_name="Supino")], [], context=context)
    assert "exercise_supported" in gaps[0]["fields"]


def test_allocation_options_preserve_source_support_and_client_availability():
    sources = [
        {"passage_id": "R1", "content": "150 minutos de atividade física por semana."},
        {"passage_id": "R2", "content": "Você pode caminhar e dividir a prática em blocos."},
    ]
    context = {
        "client_answers": {"weekly_availability": {"value": 3}, "session_duration": {"value": 60}}
    }
    options = allocation_options(sources, context)
    assert len(options) == 1
    option = options[0]
    assert option["exercise_name"] == "Caminhada"
    assert option["repetitions"] == "50 minutos"
    assert option["supporting_passages"] == ["R1", "R2"]
    assert (
        prescription_gaps([option], sources, context=context, objective=option["objective"]) == []
    )
    context["client_answers"]["session_duration"]["value"] = 30
    assert allocation_options(sources, context) == []
    assert allocation_options(sources, {}) == []
    assert allocation_options(sources[:1], context) == []


def test_weekly_duration_cannot_borrow_another_intensity_condition():
    sources = [
        {
            "passage_id": "R1",
            "content": "Se preferir atividades vigorosas, pratique 75 minutos por semana. "
            "Pode dividir a prática. Você pode caminhar.",
        },
        {
            "passage_id": "R2",
            "content": "Se preferir atividades moderadas, pratique 150 minutos por semana.",
        },
    ]
    context = {
        "client_answers": {"weekly_availability": {"value": 3}, "session_duration": {"value": 60}}
    }
    walking = item(
        exercise_name="Caminhada",
        sets=1,
        repetitions="25 minutos",
        rest_seconds=0,
        load_guidance="Ritmo moderado.",
    )
    objective = "75 minutos por semana em 3 dias de 25 minutos."
    gaps = prescription_gaps([walking], sources, context=context, objective=objective)
    assert "load_supported" in gaps[0]["fields"]
    walking["load_guidance"] = "Intensidade vigorosa."
    assert prescription_gaps([walking], sources, context=context, objective=objective) == []
    walking["load_guidance"] = "Ritmo confortável."
    assert prescription_gaps([walking], sources, context=context, objective=objective)
    walking.update(repetitions="50 minutos", load_guidance="Intensidade moderada.")
    objective = "150 minutos por semana em 3 dias de 50 minutos."
    assert prescription_gaps([walking], sources, context=context, objective=objective) == []
    options = allocation_options(sources, context)
    assert {(o["repetitions"], o["intensity"]) for o in options} == {
        ("25 minutos", "vigorosa"),
        ("50 minutos", "moderada"),
    }
    assert all(o["intensity"] in o["objective"] for o in options)


def test_english_intensity_clauses_and_decimal_commas_keep_their_conditions():
    sources = refs(
        "Walking: 150 minutes of moderate activity per week or 75 minutes of vigorous "
        "activity per week. You can divide the practice."
    )
    rows = source_parameters(sources, 3)[0]["weekly_prescriptions"]
    assert [(r["seconds"], r["intensity"]) for r in rows] == [
        ((9000, 9000), "moderada"),
        ((4500, 4500), "vigorosa"),
    ]
    source = refs("Agachamento: 2 séries de 8 repetições, descanso de 1,5 minutos.")
    assert prescription_gaps([item()], source, context={}) == []
    ambiguous = refs(
        "150 minutos de atividade moderada e vigorosa por semana. Pode dividir e caminhar."
    )
    assert (
        allocation_options(ambiguous, {"client_answers": {"weekly_availability": {"value": 3}}})
        == []
    )
