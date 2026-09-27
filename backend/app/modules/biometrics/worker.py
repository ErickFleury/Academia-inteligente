"""Restart-safe cleanup. An unavailable provider never prevents app startup."""

import asyncio
import logging
from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.modules.biometrics.config import BiometricConfig, BiometricError
from app.modules.biometrics.enrollment import EnrollmentService

logger = logging.getLogger(__name__)


def cleanup_once(rebuild=False):
    if SessionLocal is None:
        return
    try:
        config = BiometricConfig.from_environment()
        if config.mode == "disabled":
            return
        with SessionLocal() as session:
            if rebuild:
                from app.modules.biometrics.access import rebuild_access_states

                rebuild_access_states(session)
            EnrollmentService(config).cleanup(session, limit=4)
    except (BiometricError, SQLAlchemyError):
        # Never log DB exception parameters, captures, provider URLs, or keys.
        logger.warning("Biometric cleanup pending; scheduled retry remains enabled")


async def cleanup_loop():
    rebuild = True
    while True:
        started = asyncio.get_running_loop().time()
        await asyncio.to_thread(cleanup_once, rebuild)
        rebuild = False
        elapsed = asyncio.get_running_loop().time() - started
        await asyncio.sleep(max(0, 60 - elapsed))


@asynccontextmanager
async def biometric_lifespan(app):
    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
