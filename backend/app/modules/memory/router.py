from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.memory.service import MemoryError, MemoryService

router = APIRouter(prefix="/ai/memory", tags=["ai-memory"])
Database = Annotated[Session, Depends(get_database_session)]
Owner = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
]
service = MemoryService()


@router.get("")
def get_memory(session: Database, owner: Owner):
    try:
        return service.snapshot(session, service.client_id_for_subject(session, owner.subject))
    except MemoryError as error:
        raise HTTPException(error.status, error.code) from None


class Correction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=400)


@router.patch("/{fact_id}")
def correct_memory(fact_id: UUID, body: Correction, session: Database, owner: Owner):
    try:
        return service.edit(
            session,
            service.client_id_for_subject(session, owner.subject),
            fact_id,
            body.revision,
            body.text,
        )
    except MemoryError as error:
        raise HTTPException(error.status, error.code) from None


@router.delete("/{fact_id}")
def forget_memory(fact_id: UUID, session: Database, owner: Owner, revision: int = Query(ge=0)):
    try:
        return service.edit(
            session, service.client_id_for_subject(session, owner.subject), fact_id, revision
        )
    except MemoryError as error:
        raise HTTPException(error.status, error.code) from None
