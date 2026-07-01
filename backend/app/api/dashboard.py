from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import CostGroupResponse, ResourceRowResponse, SpendSummaryResponse, TrendPointResponse
from app.services.dashboard_service import get_cost_groups, get_resource_inventory_rows, get_spend_summary, get_spend_trend
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=SpendSummaryResponse)
async def read_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SpendSummaryResponse:
    return await get_spend_summary(db, current_user)


@router.get("/by-service", response_model=list[CostGroupResponse])
async def read_by_service(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> list[CostGroupResponse]:
    return await get_cost_groups(db, current_user, dimension="service", start=start, end=end)


@router.get("/by-region", response_model=list[CostGroupResponse])
async def read_by_region(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> list[CostGroupResponse]:
    return await get_cost_groups(db, current_user, dimension="region", start=start, end=end)


@router.get("/trend", response_model=list[TrendPointResponse])
async def read_trend(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    granularity: Literal["daily", "monthly"] = Query(default="daily"),
) -> list[TrendPointResponse]:
    return await get_spend_trend(db, current_user, start=start, end=end, granularity=granularity)


@router.get("/resources", response_model=list[ResourceRowResponse])
async def read_resources(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ResourceRowResponse]:
    return await get_resource_inventory_rows(db, current_user)
