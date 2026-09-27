"""Seed singleton infrastructure when fixtures use create_all instead of migrations."""

from sqlalchemy import event

from app.modules.biometrics.models import BiometricLock


@event.listens_for(BiometricLock.__table__, "after_create")
def seed_biometric_lock(table, connection, **kwargs):
    connection.execute(table.insert().values(id=1))
