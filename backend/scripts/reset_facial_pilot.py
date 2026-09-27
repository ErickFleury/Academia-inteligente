"""Explicit owner-only local test reset; default is a read-only inventory.

Stop the backend before --apply and keep it stopped if reconciliation fails.
Never use this procedure after beginning real enrollment. Prints counts only.
"""

import argparse
import json
import os
from urllib.parse import urlparse

from sqlalchemy import delete, func, inspect, or_, select, text, update

from app.database import Base, SessionLocal
from app.main import app  # noqa: F401 - register all domain metadata
from app.modules.biometrics.config import BiometricConfig
from app.modules.biometrics.provider import CompreFaceProvider
from app.modules.clients.models import Account
from app.modules.identity.keycloak_admin import KeycloakAdminClient, KeycloakAdminConfig

PRESERVED_TABLES = {
    "account",
    "biometric_lock",
    "equipment_model",
    "equipment_unit",
    "equipment_image",
}
RESET_TABLES = {
    "person_profile",
    "client",
    "employee",
    "client_identity_reconciliation",
    "employee_identity_reconciliation",
    "onboarding_invitation",
    "onboarding",
    "onboarding_audit_event",
    "onboarding_ai_conversation",
    "onboarding_ai_message",
    "training_plan",
    "training_plan_version",
    "training_plan_item",
    "training_ai_conversation",
    "training_ai_message",
    "training_adaptation_proposal",
    "training_adaptation_operation",
    "progress_update",
    "social_profile",
    "profile_image",
    "client_follow",
    "client_follow_request",
    "post_like",
    "post_comment",
    "post_image",
    "comment_image",
    "social_moderation_audit",
    "profile_presence_preference",
    "profile_presence_consent_audit",
    "client_access_reference",
    "access_passage_event",
    "occupancy_correction",
    "access_source_heartbeat",
    "biometric_enrollment",
    "biometric_enrollment_session",
    "biometric_cleanup_job",
    "biometric_command",
    "biometric_audit",
    "biometric_client_access_state",
    "biometric_recognition_attempt",
    "biometric_release_request",
}


def require_local_environment():
    if (
        urlparse(os.environ.get("DATABASE_URL", "")).hostname != "postgres"
        or KeycloakAdminConfig.from_environment().base_url != "http://keycloak:8080"
        or KeycloakAdminConfig.from_environment().realm != "academia"
    ):
        raise RuntimeError("Reset is limited to the approved local Docker deployment")
    BiometricConfig.from_environment().require_pilot()
    if not os.environ.get("APP_ADMIN_USERNAME"):
        raise RuntimeError("Bootstrap administrator configuration is required")


def list_users(identity):
    token = identity._access_token()
    result = []
    while True:
        rows = identity._request(
            "GET", f"/admin/realms/academia/users?first={len(result)}&max=100", token
        )
        if not isinstance(rows, list):
            raise RuntimeError("Identity inventory unavailable")
        result.extend(rows)
        if len(rows) < 100:
            return result


def protected_users(identity, users, username):
    admins = [row for row in users if row.get("username") == username]
    if len(admins) != 1 or not admins[0].get("enabled"):
        raise RuntimeError("The configured bootstrap administrator must exist and be enabled")
    admin_id = admins[0]["id"]
    roles = identity._request(
        "GET",
        f"/admin/realms/academia/users/{admin_id}/role-mappings/realm/composite",
        identity._access_token(),
    )
    if not isinstance(roles, list) or not any(row.get("name") == "admin" for row in roles):
        raise RuntimeError("Bootstrap administrator authorization is unavailable")
    return {admin_id} | {row["id"] for row in users if row.get("serviceAccountClientId")}


def subjects(provider):
    rows = provider._request("GET", "/subjects").get("subjects")
    if not isinstance(rows, list) or not all(isinstance(row, str) for row in rows):
        raise RuntimeError("Provider inventory unavailable")
    return rows


def table_counts(session):
    return {
        name: session.scalar(select(func.count()).select_from(Base.metadata.tables[name]))
        for name in sorted(Base.metadata.tables)
    }


def validate_schema(session):
    expected = RESET_TABLES | PRESERVED_TABLES
    actual = set(inspect(session.connection()).get_table_names()) - {"alembic_version"}
    if set(Base.metadata.tables) != expected or actual != expected:
        raise RuntimeError("Schema changed; review the reset table allowlist before proceeding")


def clear_database(session, protected):
    """Atomic, explicit table allowlist; no CASCADE and no equipment/configuration writes."""
    validate_schema(session)
    names = ", ".join('"' + name + '"' for name in sorted(RESET_TABLES))
    session.execute(text("TRUNCATE TABLE " + names))
    session.execute(
        delete(Account).where(
            or_(Account.keycloak_subject.is_(None), Account.keycloak_subject.not_in(protected))
        )
    )
    session.execute(update(Base.metadata.tables["biometric_lock"]).values(capture_until=None))
    session.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Erase the previously authorized local test data"
    )
    options = parser.parse_args()
    require_local_environment()
    identity = KeycloakAdminClient()
    provider = CompreFaceProvider(BiometricConfig.from_environment())
    provider.ready()
    users = list_users(identity)
    protected = protected_users(identity, users, os.environ["APP_ADMIN_USERNAME"])
    face_subjects = subjects(provider)
    with SessionLocal() as session:
        counts = table_counts(session)
        if not options.apply:
            print(
                json.dumps(
                    {
                        "mode": "inventory",
                        "database_rows": counts,
                        "test_identity_users": len(users) - len(protected),
                        "protected_identity_users": len(protected),
                        "provider_subjects": len(face_subjects),
                    }
                )
            )
            return
        if face_subjects or counts["biometric_enrollment"]:
            raise RuntimeError(
                "Facial enrollment already exists; review before erasing newly enrolled data"
            )
        # Prevent every application writer while reconciling identity/provider state.
        names = ", ".join('"' + name + '"' for name in sorted(Base.metadata.tables))
        session.execute(text("SET LOCAL lock_timeout = '10s'"))
        session.execute(text("LOCK TABLE " + names + " IN ACCESS EXCLUSIVE MODE"))
        validate_schema(session)  # fail before any external identity is removed
        equipment = {
            name: session.execute(select(Base.metadata.tables[name])).all()
            for name in ("equipment_model", "equipment_unit", "equipment_image")
        }
        for user in users:
            if user["id"] not in protected:
                identity.delete_identity(user["id"])
        remaining = list_users(identity)
        if {row["id"] for row in remaining} != protected or subjects(provider):
            raise RuntimeError("External reset incomplete; leave backend stopped and reconcile")
        clear_database(session, protected)
        after = table_counts(session)
        if any(after[name] for name in RESET_TABLES):
            raise RuntimeError("Application reset incomplete")
        if any(
            session.execute(select(Base.metadata.tables[name])).all() != rows
            for name, rows in equipment.items()
        ):
            raise RuntimeError("Equipment preservation check failed")
        protected_users(identity, remaining, os.environ["APP_ADMIN_USERNAME"])
        session.commit()
        print(
            json.dumps(
                {
                    "mode": "applied",
                    "removed_identity_users": len(users) - len(protected),
                    "protected_identity_users": len(remaining),
                    "provider_subjects": 0,
                    "remaining_test_data_rows": sum(after[name] for name in RESET_TABLES),
                    "equipment_models": after["equipment_model"],
                    "equipment_units": after["equipment_unit"],
                }
            )
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # No SQL/provider payloads, personal data or environment values in operational output.
        raise SystemExit(
            "Pilot reset did not complete. Keep the backend stopped after an apply failure "
            "and review local reconciliation."
        ) from None
