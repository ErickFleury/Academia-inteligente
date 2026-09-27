"""Explicit synthetic enrollment arrangement for pre-existing registration API tests."""

from uuid import UUID, uuid4

from app.modules.biometrics.config import BiometricConfig, BiometricError
from app.modules.biometrics.enrollment import EnrollmentService
from app.modules.biometrics.provider import Face
from app.modules.biometrics.router import get_enrollment_service


class SyntheticFaces:
    def inspect(self, image):
        return (Face(0.99, ()),)

    def enroll(self, subject, image):
        pass

    def delete(self, subject):
        pass

    def ready(self):
        pass


def prepare_enrolled_registration(app, session, actor="test-subject"):
    service = EnrollmentService(BiometricConfig(mode="pilot", api_key="fixture"), SyntheticFaces())
    app.dependency_overrides[get_enrollment_service] = lambda: service

    def prepare(role, payload):
        payload = {**payload, "command_id": str(uuid4())}
        try:
            stage = service.create(
                session, actor, uuid4(), email=payload["email"], cpf=payload["cpf"], role=role
            )
            identifier = UUID(stage["session_id"])
            service.capture(session, actor, identifier, uuid4(), b"synthetic")
            payload["enrollment_session_id"] = str(identifier)
        except BiometricError:
            session.rollback()  # preserve ordinary invalid/duplicate identity assertions
        return payload

    return prepare
