from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.deps import get_health_service
from app.schemas.health import HealthResponse, ServiceHealthResponse
from app.services.health import HealthService

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health_check(service: HealthService = Depends(get_health_service)) -> HealthResponse:
    """Report reachability without exposing credentials."""
    return service.check()


@router.get("/ready", response_model=HealthResponse)
def readiness_check(service: HealthService = Depends(get_health_service)) -> HealthResponse | JSONResponse:
    result = service.check()
    if result.status != "ok":
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=result.model_dump())
    return result


@router.get("/database-health", response_model=ServiceHealthResponse)
def database_health(service: HealthService = Depends(get_health_service)) -> ServiceHealthResponse:
    result = service.database_health()
    if result.status != "ok":
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=result.model_dump())
    return result


@router.get("/worker-health", response_model=ServiceHealthResponse)
def worker_health(service: HealthService = Depends(get_health_service)) -> ServiceHealthResponse:
    result = service.worker_health()
    if result.status != "ok":
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=result.model_dump())
    return result
