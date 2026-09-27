"""Extend the existing person-erasure transaction; provider deletion is durable."""

from datetime import timedelta

from sqlalchemy import delete, or_, select

from app.modules.biometrics.enrollment import aware, identity_binding, lock_biometrics, utcnow
from app.modules.biometrics.models import (
    BiometricAudit,
    BiometricCleanupJob,
    BiometricCommand,
    BiometricEnrollment,
    EnrollmentSession,
)


def erase_person_biometrics(session, account):
    """Caller owns Account lock and commit; no identifying tombstone remains."""
    lock_biometrics(session)
    binding = (
        identity_binding(account.email, account.person_profile.cpf)
        if account.person_profile
        else None
    )
    stages = session.scalars(
        select(EnrollmentSession).where(
            or_(
                EnrollmentSession.account_id == account.id,
                EnrollmentSession.identity_binding == binding,
            )
        )
    ).all()
    stage_ids = [row.id for row in stages]
    subjects = {row.subject for row in stages if row.subject}
    enrollment = session.get(BiometricEnrollment, account.id)
    if enrollment:
        subjects.add(enrollment.subject)
    jobs = session.scalars(
        select(BiometricCleanupJob).where(
            or_(
                BiometricCleanupJob.account_id == account.id,
                BiometricCleanupJob.session_id.in_(stage_ids),
            )
        )
    ).all()
    by_subject = {job.subject: job for job in jobs}
    for subject in subjects:
        if subject not in by_subject:
            job = BiometricCleanupJob(subject=subject, due_at=utcnow())
            session.add(job)
            by_subject[subject] = job
    capture_deadlines = {
        row.subject: aware(row.capture_until) + timedelta(seconds=60)
        for row in stages
        if row.subject and row.status == "capturing"
    }
    for job in by_subject.values():
        job.account_id = None
        job.session_id = None
        job.due_at = max(utcnow(), capture_deadlines.get(job.subject, utcnow()))
    session.flush()
    for model in (BiometricAudit, BiometricCommand):
        session.execute(
            delete(model).where(
                or_(model.account_id == account.id, model.session_id.in_(stage_ids))
            )
        )
    session.execute(delete(EnrollmentSession).where(EnrollmentSession.id.in_(stage_ids)))
    session.execute(delete(BiometricEnrollment).where(BiometricEnrollment.account_id == account.id))
