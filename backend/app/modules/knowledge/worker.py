"""Persisted import jobs, processed one at a time without a message broker."""

import asyncio
import logging
from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError

from app import database
from app.integrations.ai import AiProviderError
from app.modules.biometrics.worker import biometric_lifespan
from app.modules.knowledge.service import KnowledgeService

logger = logging.getLogger(__name__)


def import_once():
    if database.SessionLocal is None:
        return False
    try:
        return KnowledgeService().import_next(database.SessionLocal)
    except (SQLAlchemyError, AiProviderError):
        logger.warning("Reference import pending; controlled retry scheduled")
        return False


async def import_loop():
    while True:
        processed = await asyncio.to_thread(import_once)
        await asyncio.sleep(0.1 if processed else 5)


@asynccontextmanager
async def assistant_lifespan(app):
    async with biometric_lifespan(app):
        task = asyncio.create_task(import_loop())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
