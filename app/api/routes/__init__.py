from fastapi import APIRouter

from app.api.routes.configurations import router as configurations_router
from app.api.routes.health import router as health_router
from app.api.routes.logs import router as logs_router
from app.api.routes.messages import router as messages_router
from app.api.routes.schema import router as schema_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(configurations_router)
api_router.include_router(schema_router)
api_router.include_router(messages_router)
api_router.include_router(logs_router)
