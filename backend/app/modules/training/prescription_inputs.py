"""Intentional collection of only the request facts authorized by the actual contract."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import AwareDatetime, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.modules.training.prescription_contract import (
    ConfirmedFact,
    DevelopmentSchedule,
    InputSnapshot,
    PrescriptionRejection,
    record_hash,
)
from app.modules.training.prescription_development import (
    DevelopmentInputConfirmation,
    _input_origin,
)
from app.modules.training.prescription_policy import Record


class RequestObservation(Record):
    value: str | bool | int | float
    observed_at: AwareDatetime | None = None
    measurement_method: str | None = None
    measurement_unit: str | None = None
    measurement_convention: str | None = None
    exercise_key: str | None = None
    variation_key: str | None = None


class RequestInputSubmission(Record):
    expected_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    values: dict[str, RequestObservation] = Field(min_length=1, max_length=20)
    schedule: DevelopmentSchedule | None = None


def input_requirements(context, actor_role, labels):
    snapshot = context["snapshot"]
    return {
        "snapshot_hash": record_hash(snapshot),
        "requirements": [
            {
                "key": r.key,
                "label": labels.get(r.key, "Informação necessária para o pedido"),
                "source": r.source,
                "can_provide": r.source == "request"
                and r.collection_approved
                and actor_role in r.allowed_actor_roles,
                "value": snapshot.facts[r.key].value if r.key in snapshot.facts else None,
                "value_type": "boolean"
                if r.key
                in {
                    "adult_eligibility",
                    "schedule_confirmed",
                    "progression_observed",
                    "observed_control",
                    "support_available",
                    "supervision_confirmed",
                }
                else "number"
                if r.key in {"baseline_capacity", "completed_attempts", "height_cm", "weight_kg"}
                else "text",
                "measurement": next(
                    (
                        {
                            "measurement_method": r.measurement_method,
                            "measurement_unit": "kg",
                            "exercise_key": c.exercise_key,
                            "variation_key": c.variation_key,
                            "measurement_convention": c.load_convention,
                        }
                        for c in context["execution"].calculations.values()
                        if c.baseline_fact == r.key
                    ),
                    None,
                ),
            }
            for r in context["execution"].input_requirements
        ],
    }


def submit_request_inputs(session, context, data, *, actor_role, actor_subject):
    original = context["snapshot"]
    if record_hash(original) != data.expected_snapshot_hash:
        raise PrescriptionRejection("missing_input", "confirmation_snapshot_changed")
    requirements = {r.key: r for r in context["execution"].input_requirements}
    snapshot = original.model_copy(deep=True)
    now, identifier = datetime.now(UTC), str(uuid4())
    for key, value in data.values.items():
        requirement = requirements.get(key)
        if (
            requirement is None
            or requirement.source != "request"
            or not requirement.collection_approved
            or actor_role not in requirement.allowed_actor_roles
        ):
            raise PrescriptionRejection("missing_input", "request_fact_authority_not_approved")
        if (
            value.observed_at is not None
            and value.observed_at > now
            or requirement.measurement_method is not None
            and value.measurement_method != requirement.measurement_method
        ):
            raise PrescriptionRejection("missing_input", "request_observation_provenance_invalid")
        try:
            snapshot.facts[key] = ConfirmedFact(
                **value.model_dump(exclude={"observed_at"}),
                source="request",
                source_id=identifier,
                source_revision=record_hash(value),
                source_actor_role=actor_role,
                source_actor_subject=actor_subject,
                confirmed_by=actor_role,
                confirmed_by_subject=actor_subject,
                observed_at=value.observed_at or now,
                confirmed_at=now,
            )
        except ValidationError:
            raise PrescriptionRejection(
                "missing_input", "request_observation_provenance_invalid"
            ) from None
    if data.schedule is not None:
        if (
            data.values.get("schedule_confirmed") is None
            or data.values["schedule_confirmed"].value is not True
        ):
            raise PrescriptionRejection("missing_input", "weekly_schedule_missing")
        snapshot.schedule = data.schedule
    try:
        snapshot = InputSnapshot.model_validate(snapshot.model_dump())
    except ValidationError:
        raise PrescriptionRejection("missing_input", "request_fact_invalid") from None
    try:
        session.add(
            DevelopmentInputConfirmation(
                client_id=snapshot.client_id,
                origin_sha256=_input_origin(original),
                snapshot=snapshot.model_dump(mode="json"),
            )
        )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise PrescriptionRejection(
            "technical_unavailability", "input_storage_unavailable"
        ) from None
    return {"status": "confirmed", "snapshot_hash": record_hash(snapshot)}
