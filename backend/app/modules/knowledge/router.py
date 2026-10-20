from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.knowledge.service import KnowledgeError, KnowledgeService

router = APIRouter(prefix="/ai/references", tags=["ai-references"])
Database = Annotated[Session, Depends(get_database_session)]
Administrator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin"))
]


def get_knowledge_service():
    return KnowledgeService()


Service = Annotated[KnowledgeService, Depends(get_knowledge_service)]


@router.get("")
def list_references(session: Database, administrator: Administrator, service: Service):
    return service.list(session)


@router.post("", status_code=202)
def upload_reference(
    session: Database,
    administrator: Administrator,
    service: Service,
    title: Annotated[str, Query(min_length=1, max_length=200)],
    media_type: Literal["application/pdf", "text/plain", "text/markdown"],
    source_id: UUID | None = None,
    raw: bytes = Body(media_type="application/octet-stream"),
):
    try:
        return service.upload(
            session, title=title, media_type=media_type, raw=raw, source_id=source_id
        )
    except KnowledgeError as error:
        raise HTTPException(error.status, error.code) from None


@router.get("/{version_id}/preview")
def preview_reference(
    version_id: UUID,
    session: Database,
    administrator: Administrator,
    service: Service,
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.preview(session, version_id, offset)
    except KnowledgeError as error:
        raise HTTPException(error.status, error.code) from None


class ReferenceAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["activate", "withdraw", "retry"]
    revision: int = Field(ge=1)


@router.post("/{version_id}/actions")
def reference_action(
    version_id: UUID,
    body: ReferenceAction,
    session: Database,
    administrator: Administrator,
    service: Service,
):
    try:
        return service.transition(session, version_id, body.action, body.revision)
    except KnowledgeError as error:
        raise HTTPException(error.status, error.code) from None
