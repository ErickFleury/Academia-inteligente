import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.health.router import router as health_router
from app.http_security import HttpSecurityMiddleware
from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.router import router as biometrics_router
from app.modules.biometrics.worker import biometric_lifespan
from app.modules.clients.instructor_router import router as instructor_clients_router
from app.modules.clients.router import router as clients_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.employees.instructor_social_router import router as instructor_social_router
from app.modules.employees.router import router as employees_router
from app.modules.equipment.instructor_router import router as instructor_equipment_router
from app.modules.equipment.router import router as equipment_router
from app.modules.identity.router import router as identity_router
from app.modules.occupancy.router import router as occupancy_router
from app.modules.onboarding.instructor_router import router as instructor_onboarding_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.presence.router import router as presence_router
from app.modules.progress.router import router as progress_router
from app.modules.social.router import router as social_router
from app.modules.training.collections_router import router as training_collections_router
from app.modules.training.router import router as training_router


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=biometric_lifespan,
        title="Academia Inteligente API",
        version="0.1.0",
        description="Foundation API; business endpoints are introduced in their owning tasks.",
    )

    @app.exception_handler(BiometricError)
    async def biometric_error(request, error):
        return JSONResponse(status_code=error.status, content={"detail": error.code})

    allowed_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    app.add_middleware(HttpSecurityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Access-Integration-Secret",
            "X-Onboarding-Token",
        ],
    )
    app.include_router(health_router)
    app.include_router(biometrics_router)
    app.include_router(identity_router)
    app.include_router(clients_router)
    app.include_router(instructor_clients_router)
    app.include_router(employees_router)
    app.include_router(instructor_social_router)
    app.include_router(dashboard_router)
    app.include_router(equipment_router)
    app.include_router(instructor_equipment_router)
    app.include_router(onboarding_router)
    app.include_router(instructor_onboarding_router)
    app.include_router(occupancy_router)
    app.include_router(presence_router)
    app.include_router(progress_router)
    app.include_router(social_router)
    app.include_router(training_router)
    app.include_router(training_collections_router)
    return app


app = create_app()
