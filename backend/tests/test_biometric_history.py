import base64
import json
from uuid import uuid4

import pytest
from test_biometric_access import access as access
from test_biometric_access import known_client, recognize
from test_biometrics_enrollment import service as service
from test_clients import AsgiClient
from test_clients import database_session as database_session

from app.database import get_database_session
from app.main import create_app
from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.enrollment import utcnow
from app.modules.biometrics.history import event_history, provider_status
from app.modules.biometrics.models import BiometricAudit
from app.modules.biometrics.passages import PassageService
from app.modules.biometrics.router import get_access_service
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity


def verify_pagination(session, service, access):
    person_id, client_id = known_client(session, service, access)
    recognize(access, session)
    now = utcnow()
    for _ in range(24):
        session.add(
            BiometricAudit(
                actor="admin",
                account_id=person_id,
                operation="enrollment_attach",
                outcome="enabled",
                created_at=now,
            )
        )
    session.commit()
    PassageService(access.config, access.provider).correct(
        session, "admin", uuid4(), client_id, True, 0, "Entrada omitida"
    )
    complete = event_history(session, limit=100)["items"]
    rows, cursor = [], None
    while True:
        page = event_history(session, limit=5, cursor=cursor)
        rows.extend(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
        assert len(rows) < 100
    assert rows == complete
    assert len({(row["kind"], row["id"]) for row in rows}) == len(rows)
    corrections = event_history(session, client_id=client_id, result="corrected", direction="entry")
    assert len(corrections["items"]) == 1
    assert corrections["items"][0]["reason"] == "Entrada omitida"
    assert all(row["person_name"] for row in event_history(session, client_id=client_id)["items"])
    assert event_history(session, client_id=uuid4())["items"] == []
    assert all(
        set(row)
        == {
            "id",
            "kind",
            "occurred_at",
            "operation",
            "result",
            "client_id",
            "person_name",
            "direction",
            "reason",
        }
        for row in rows
    )


def test_history_is_bounded_filterable_and_safe(database_session, service, access):
    verify_pagination(database_session, service, access)


@pytest.mark.parametrize(
    "cursor",
    [
        "invalid",
        "e30=",
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "time": "2026-09-27T00:00:00+00:00",
                    "kind": "audit",
                    "id": 5,
                }
            ).encode()
        ).decode(),
    ],
)
def test_malformed_cursor_is_controlled(database_session, cursor):
    with pytest.raises(BiometricError, match="history_cursor_invalid"):
        event_history(database_session, cursor=cursor)


def test_provider_failure_returns_only_safe_status(database_session, access):
    assert provider_status(database_session, access)["available"]
    access.provider.failure = True
    assert provider_status(database_session, access) == {
        "mode": "pilot",
        "available": False,
        "cleanup_pending": 0,
    }


def test_history_api_limits_and_admin_only(database_session, access):
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: database_session
    app.dependency_overrides[get_access_service] = lambda: access
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "admin", None, ("admin",)
    )
    http = AsgiClient(app)
    assert http.get("/biometrics/events").json() == {"items": [], "next_cursor": None}
    assert http.get("/biometrics/events?limit=101").status_code == 422
    assert http.get("/biometrics/events?cursor=invalid").status_code == 422
    assert http.get("/biometrics/provider-status").status_code == 200
    for role in ("client", "instructor", "attendant"):
        app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
            "other", None, (role,)
        )
        for path in ("/biometrics/events", "/biometrics/provider-status"):
            assert http.get(path).status_code == 403
    del app.dependency_overrides[get_authenticated_identity]
    assert http.get("/biometrics/events").status_code == 401
