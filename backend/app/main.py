import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.health.router import router as health_router
from app.modules.clients.router import router as clients_router
from app.modules.equipment.router import router as equipment_router
from app.modules.identity.router import router as identity_router
from app.modules.occupancy.router import router as occupancy_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.progress.router import router as progress_router
from app.modules.training.router import router as training_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Academia Inteligente API",
        version="0.1.0",
        description="Foundation API; business endpoints are introduced in their owning tasks.",
    )
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Access-Integration-Secret"],
    )
    app.include_router(health_router)
    app.include_router(identity_router)
    app.include_router(clients_router)
    app.include_router(equipment_router)
    app.include_router(onboarding_router)
    app.include_router(occupancy_router)
    app.include_router(progress_router)
    app.include_router(training_router)
    return app


app = create_app()
