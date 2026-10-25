"""Transport-only instructor evidence review and confidential custody endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training import evidence_review as service
from app.modules.training.evidence_review_schema import (
    ArtifactOut,
    JudgmentInput,
    JudgmentOut,
    SealCasesOut,
    SealInput,
    SealOut,
)


def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/training/evidence-review",
    tags=["training-evidence-review"],
    dependencies=[Depends(no_store)],
)
Database = Annotated[Session, Depends(get_database_session)]
Instructor = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "instructor"))
]


def invoke(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except service.EvidenceReviewError as error:
        raise HTTPException(error.status, error.code) from None
    except SQLAlchemyError:
        for arg in args:
            if isinstance(arg, Session):
                arg.rollback()
        raise HTTPException(503, "review_storage_unavailable") from None


@router.get("/artifacts", response_model=list[ArtifactOut])
def artifacts(session: Database, instructor: Instructor):
    invoke(service.require_instructor, session, instructor)
    return [
        invoke(service.artifact_out, session, item, details=False)
        for item in invoke(service.review_artifacts, session).values()
    ]


@router.get("/readiness")
def readiness(session: Database, instructor: Instructor):
    from app.modules.training.prescription_authorization import readiness_matrix

    invoke(service.require_instructor, session, instructor)
    try:
        return readiness_matrix()
    except (OSError, ValueError, KeyError):
        raise HTTPException(503, "review_artifacts_unavailable") from None


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
def artifact(artifact_id: str, session: Database, instructor: Instructor):
    invoke(service.require_instructor, session, instructor)
    return invoke(
        service.artifact_out,
        session,
        invoke(service._artifact, artifact_id, session=session),
        details=True,
        subject=instructor.subject,
    )


@router.post("/artifacts/{artifact_id}/judgments", response_model=JudgmentOut)
def register_judgment(
    artifact_id: str, data: JudgmentInput, session: Database, instructor: Instructor
):
    return invoke(service.register_judgment, session, instructor, artifact_id, data)


@router.get("/seals", response_model=list[SealOut])
def seals(session: Database, instructor: Instructor):
    return invoke(service.list_seals, session, instructor)


@router.get("/judgments/{judgment_id}", response_model=JudgmentOut)
def judgment(judgment_id: UUID, session: Database, instructor: Instructor):
    return invoke(service.get_judgment, session, instructor, judgment_id)


@router.post("/seals", response_model=SealOut)
def register_seal(data: SealInput, session: Database, instructor: Instructor):
    return invoke(service.register_seal, session, instructor, data)


@router.get("/seals/{seal_id}/cases", response_model=SealCasesOut)
def cases(seal_id: UUID, session: Database, instructor: Instructor):
    return invoke(service.private_cases, session, instructor, seal_id)
