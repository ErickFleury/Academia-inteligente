from app.health.router import health
from app.main import create_app


def test_health_handler_returns_ok() -> None:
    assert health() == {"status": "ok"}


def test_openapi_documents_foundation_modules() -> None:
    document = create_app().openapi()

    assert document["info"]["title"] == "Academia Inteligente API"
    assert "/health" in document["paths"]
