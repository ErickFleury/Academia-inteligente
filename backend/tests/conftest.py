"""Seed singleton infrastructure when fixtures use create_all instead of migrations."""

import pytest
from sqlalchemy import event

from app.modules.biometrics.models import BiometricLock


@pytest.fixture(autouse=True)
def historical_evidence_contract(monkeypatch):
    """Legacy fixtures are not approved research; owner-RAG suites opt in explicitly."""
    monkeypatch.setenv("TRAINING_EVIDENCE_MODE", "legacy")


@event.listens_for(BiometricLock.__table__, "after_create")
def seed_biometric_lock(table, connection, **kwargs):
    connection.execute(table.insert().values(id=1))
