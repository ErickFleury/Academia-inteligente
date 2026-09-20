from fastapi import FastAPI

from app.health.router import router as health_router
from app.modules.clients.router import router as clients_router
from app.modules.identity.router import router as identity_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.training.router import router as training_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Academia Inteligente API",
        version="0.1.0",
        description="Foundation API; business endpoints are introduced in their owning tasks.",
    )
    app.include_router(health_router)
    app.include_router(identity_router)
    app.include_router(clients_router)
    app.include_router(onboarding_router)
    app.include_router(training_router)
    return app


app = create_app()
