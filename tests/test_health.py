from fastapi.testclient import TestClient

from app.api.deps import get_health_service
from app.main import create_app
from app.schemas.health import DependencyStatus, HealthResponse


class HealthyService:
    def check(self) -> HealthResponse:
        return HealthResponse(status="ok", database=DependencyStatus(status="ok"), redis=DependencyStatus(status="ok"))


class DegradedService:
    def check(self) -> HealthResponse:
        return HealthResponse(status="degraded", database=DependencyStatus(status="ok"), redis=DependencyStatus(status="error"))


def test_health_reports_dependency_status() -> None:
    application = create_app()
    application.dependency_overrides[get_health_service] = HealthyService
    with TestClient(application) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_returns_503_when_a_dependency_is_unavailable() -> None:
    application = create_app()
    application.dependency_overrides[get_health_service] = DegradedService
    with TestClient(application) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["redis"]["status"] == "error"
