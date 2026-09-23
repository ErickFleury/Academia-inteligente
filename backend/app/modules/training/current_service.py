"""Read-only current-plan lookup scoped to the authenticated local client."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.training.models import TrainingPlan, TrainingPlanVersion


class CurrentTrainingPlanService:
    """Returns only the current version owned by the Keycloak subject's client."""

    def find_for_subject(self, session: Session, subject: str) -> TrainingPlanVersion | None:
        return session.scalar(
            select(TrainingPlanVersion)
            .join(TrainingPlan, TrainingPlanVersion.plan_id == TrainingPlan.id)
            .join(Client, TrainingPlan.client_id == Client.id)
            .join(Account, Client.account_id == Account.id)
            .where(
                Account.keycloak_subject == subject,
                TrainingPlan.is_current,
                TrainingPlanVersion.status == "current",
            )
        )

    def find_drafts_for_subject(self, session: Session, subject: str) -> list[TrainingPlanVersion]:
        """Return only the authenticated client's unapproved plan versions."""
        return list(
            session.scalars(
                select(TrainingPlanVersion)
                .join(TrainingPlan, TrainingPlanVersion.plan_id == TrainingPlan.id)
                .join(Client, TrainingPlan.client_id == Client.id)
                .join(Account, Client.account_id == Account.id)
                .where(
                    Account.keycloak_subject == subject,
                    TrainingPlanVersion.status == "proposal",
                )
                .order_by(TrainingPlanVersion.created_at.desc())
            )
        )
