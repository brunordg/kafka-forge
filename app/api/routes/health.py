from fastapi import APIRouter

from app.api.schemas.health import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
def get_health() -> HealthStatus:
    return HealthStatus(status="ok")
