from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, get_current_user, require_role
from app.models.user import User, UserRole
from app.services.forecast_service import get_service_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("")
@router.get("/service")
async def get_forecast(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    service_name: str = Query(default="total"),
    horizon_days: int = Query(default=30, ge=7, le=90),
) -> dict[str, Any]:
    filter_val = None if service_name in ("total", "all", "") else service_name
    return await get_service_forecast(
        db,
        current_user,
        service_filter=filter_val,
        horizon_days=horizon_days,
    )


@router.post("/retrain")
async def retrain_models(
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> dict[str, Any]:
    result = await get_service_forecast(db, current_user, service_filter=None, horizon_days=30)
    return {
        "message": "Forecast models successfully retrained on current historical cost records.",
        "model_name": result["model_name"],
        "mae": result["mae"],
        "rmse": result["rmse"],
        "baseline_mae": result["baseline_mae"],
        "baseline_rmse": result["baseline_rmse"],
    }
