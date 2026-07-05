from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.findings import router as findings_router
from app.api.health import router as health_router
from app.api.organization import router as organization_router
from app.api.sync import router as sync_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(findings_router)
api_router.include_router(organization_router)
api_router.include_router(sync_router)
