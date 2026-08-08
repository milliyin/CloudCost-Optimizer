from fastapi import APIRouter

from app.api.budgets import router as budgets_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.findings import router as findings_router
from app.api.forecast import router as forecast_router
from app.api.health import router as health_router
from app.api.organization import router as organization_router
from app.api.recommendations import router as recommendations_router
from app.api.reports import router as reports_router
from app.api.sync import router as sync_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(findings_router)
api_router.include_router(recommendations_router)
api_router.include_router(budgets_router)
api_router.include_router(reports_router)
api_router.include_router(forecast_router)
api_router.include_router(organization_router)
api_router.include_router(sync_router)
