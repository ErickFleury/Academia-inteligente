"""One local transaction for person/role, enrollment, and identity reconciliation."""

from uuid import UUID

from sqlalchemy import select

from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.enrollment import EnrollmentService, command, lock_biometrics
from app.modules.clients.models import Account, Client, Employee


class RegistrationService:
    def __init__(self, enrollment: EnrollmentService):
        self.enrollment = enrollment

    def create(
        self,
        session,
        *,
        actor: str,
        command_id: UUID,
        enrollment_session_id: UUID | None,
        role: str,
        data,
        service,
        cnpj=None,
        specialization=None,
    ):
        self.enrollment.config.require_pilot()
        try:
            # Existing identity writers acquire Account before biometric metadata.
            session.scalar(select(Account).where(Account.email == data.email).with_for_update())
            lock_biometrics(session)
            cmd, replay = command(
                session,
                command_id,
                actor,
                "registration_" + role,
                [data.__dict__, enrollment_session_id, cnpj, specialization],
            )
            if replay:
                item = service.get(session, UUID(cmd.result["id"]))
                if item is None:
                    raise BiometricError("registration_unavailable", 404)
                session.commit()  # release locks before background identity reconciliation
                return item
            if role == "client":
                item = service.create(session, data, commit=False)
                model = Client
            else:
                item = service.create(session, data, cnpj, specialization, commit=False)
                model = Employee
            person_id = session.get(model, item.id).account_id
            self.enrollment.attach(
                session,
                account_id=person_id,
                email=data.email,
                cpf=data.cpf,
                role=role,
                actor=actor,
                session_id=enrollment_session_id,
            )
            cmd.account_id = person_id
            cmd.result = {"id": str(item.id), "role": role}
            session.commit()
            return service.get(session, item.id)
        except Exception:
            session.rollback()
            raise
