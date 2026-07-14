from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.budget import AlertResponse, BudgetRequest, BudgetResponse
from app.services.budget_service import create_budget, list_alerts, list_budgets, update_budget

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetResponse])
async def read_budgets(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[BudgetResponse]:
    return await list_budgets(db, current_user)


@router.post("", response_model=BudgetResponse)
async def create_budget_route(
    payload: BudgetRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> BudgetResponse:
    return await create_budget(db, current_user, payload)


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget_route(
    budget_id: int,
    payload: BudgetRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> BudgetResponse:
    try:
        return await update_budget(db, current_user, budget_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/alerts", response_model=list[AlertResponse])
async def read_alerts(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AlertResponse]:
    return await list_alerts(db, current_user)
