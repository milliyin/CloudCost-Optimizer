from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.budget import Budget
from app.models.cost_record import CostRecord
from app.models.user import User
from app.schemas.budget import AlertResponse, BudgetRequest, BudgetResponse
from app.services.audit_service import add_audit_log


async def _matching_budgets(
    db: AsyncSession,
    organization_id: int,
    *,
    scope: str,
    scope_value: str,
    period: str,
    exclude_budget_id: int | None = None,
) -> list[Budget]:
    query = select(Budget).where(
        Budget.organization_id == organization_id,
        Budget.scope == scope,
        Budget.scope_value == scope_value,
        Budget.period == period,
    )
    if exclude_budget_id is not None:
        query = query.where(Budget.id != exclude_budget_id)

    return (
        await db.execute(query.order_by(Budget.created_at.desc(), Budget.id.desc()))
    ).scalars().all()


async def _current_scope_spend(db: AsyncSession, organization_id: int, budget: Budget, today: date) -> float:
    month_start = today.replace(day=1)
    if budget.scope == "region":
        amount = await db.scalar(
            select(func.coalesce(func.sum(CostRecord.amount), 0))
            .where(
                CostRecord.organization_id == organization_id,
                CostRecord.date >= month_start,
                CostRecord.date <= today,
                CostRecord.region == budget.scope_value,
                CostRecord.region != "",
            )
        )
        return float(amount or 0)

    query = select(func.coalesce(func.sum(CostRecord.amount), 0)).where(
        CostRecord.organization_id == organization_id,
        CostRecord.date >= month_start,
        CostRecord.date <= today,
        CostRecord.service != "",
    )
    if budget.scope == "service":
        query = query.where(CostRecord.service == budget.scope_value)
    amount = await db.scalar(query)
    return float(amount or 0)


async def evaluate_budgets(db: AsyncSession, organization_id: int) -> int:
    budgets = (
        await db.execute(
            select(Budget)
            .where(
                Budget.organization_id == organization_id,
                Budget.is_active.is_(True),
                Budget.scope != "region",
            )
            .order_by(Budget.id.asc())
        )
    ).scalars().all()

    today = date.today()
    period_start = today.replace(day=1)
    triggered = 0

    for budget in budgets:
        current_spend = await _current_scope_spend(db, organization_id, budget, today)
        if current_spend < float(budget.threshold_amount):
            continue

        existing = await db.scalar(
            select(Alert).where(
                Alert.organization_id == organization_id,
                Alert.budget_id == budget.id,
                Alert.period_start == period_start,
            )
        )
        if existing is None:
            db.add(
                Alert(
                    organization_id=organization_id,
                    budget_id=budget.id,
                    period_start=period_start,
                    triggered_at=datetime.now(UTC),
                    spend_at_trigger=Decimal(str(round(current_spend, 2))),
                )
            )
            triggered += 1
        else:
            existing.spend_at_trigger = Decimal(str(round(current_spend, 2)))
            existing.triggered_at = datetime.now(UTC)

    return triggered


async def list_budgets(db: AsyncSession, current_user: User) -> list[BudgetResponse]:
    budgets = (
        await db.execute(
            select(Budget)
            .where(
                Budget.organization_id == current_user.organization_id,
                Budget.scope != "region",
            )
            .order_by(Budget.created_at.desc(), Budget.id.desc())
        )
    ).scalars().all()
    seen: set[tuple[str, str, str]] = set()
    visible_budgets: list[Budget] = []
    for budget in budgets:
        key = (budget.scope, budget.scope_value, budget.period)
        if key in seen:
            continue
        seen.add(key)
        visible_budgets.append(budget)

    return [
        BudgetResponse(
            id=budget.id,
            scope=budget.scope,
            scope_value=budget.scope_value,
            threshold_amount=float(budget.threshold_amount),
            period=budget.period,
            is_active=budget.is_active,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
        )
        for budget in visible_budgets
    ]


async def create_budget(db: AsyncSession, current_user: User, payload: BudgetRequest) -> BudgetResponse:
    matches = await _matching_budgets(
        db,
        current_user.organization_id,
        scope=payload.scope,
        scope_value=payload.scope_value,
        period=payload.period,
    )
    budget = matches[0] if matches else None
    threshold_amount = Decimal(str(payload.threshold_amount))

    if budget is None:
        budget = Budget(
            organization_id=current_user.organization_id,
            owner_id=current_user.id,
            scope=payload.scope,
            scope_value=payload.scope_value,
            threshold_amount=threshold_amount,
            period=payload.period,
        )
        db.add(budget)
        await db.flush()
        action = "budget.create"
    else:
        budget.owner_id = current_user.id
        budget.scope = payload.scope
        budget.scope_value = payload.scope_value
        budget.threshold_amount = threshold_amount
        budget.period = payload.period
        budget.is_active = True
        action = "budget.update"

        for duplicate in matches[1:]:
            duplicate.is_active = False

    add_audit_log(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        action=action,
        target_type="budget",
        target_id=budget.id,
        details={
            "scope": budget.scope,
            "scope_value": budget.scope_value,
            "threshold_amount": float(budget.threshold_amount),
            "period": budget.period,
        },
    )
    await evaluate_budgets(db, current_user.organization_id)
    await db.commit()
    await db.refresh(budget)
    return BudgetResponse(
        id=budget.id,
        scope=budget.scope,
        scope_value=budget.scope_value,
        threshold_amount=float(budget.threshold_amount),
        period=budget.period,
        is_active=budget.is_active,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


async def update_budget(db: AsyncSession, current_user: User, budget_id: int, payload: BudgetRequest) -> BudgetResponse:
    budget = await db.scalar(
        select(Budget).where(
            Budget.id == budget_id,
            Budget.organization_id == current_user.organization_id,
            Budget.scope != "region",
        )
    )
    if budget is None:
        raise ValueError("Budget not found")

    duplicates = await _matching_budgets(
        db,
        current_user.organization_id,
        scope=payload.scope,
        scope_value=payload.scope_value,
        period=payload.period,
        exclude_budget_id=budget.id,
    )
    budget.scope = payload.scope
    budget.scope_value = payload.scope_value
    budget.threshold_amount = Decimal(str(payload.threshold_amount))
    budget.period = payload.period
    budget.is_active = True

    for duplicate in duplicates:
        duplicate.is_active = False

    add_audit_log(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        action="budget.update",
        target_type="budget",
        target_id=budget.id,
        details={
            "scope": budget.scope,
            "scope_value": budget.scope_value,
            "threshold_amount": float(budget.threshold_amount),
            "period": budget.period,
        },
    )
    await evaluate_budgets(db, current_user.organization_id)
    await db.commit()
    await db.refresh(budget)
    return BudgetResponse(
        id=budget.id,
        scope=budget.scope,
        scope_value=budget.scope_value,
        threshold_amount=float(budget.threshold_amount),
        period=budget.period,
        is_active=budget.is_active,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


async def list_alerts(db: AsyncSession, current_user: User) -> list[AlertResponse]:
    rows = (
        await db.execute(
            select(Alert, Budget)
            .join(Budget, Budget.id == Alert.budget_id)
            .where(Alert.organization_id == current_user.organization_id, Budget.scope != "region")
            .order_by(Alert.triggered_at.desc(), Alert.id.desc())
        )
    ).all()
    deduped_rows: list[tuple[Alert, Budget]] = []
    seen: set[tuple[str, str, date]] = set()
    for alert, budget in rows:
        key = (budget.scope, budget.scope_value, alert.period_start)
        if key in seen:
            continue
        seen.add(key)
        deduped_rows.append((alert, budget))

    return [
        AlertResponse(
            id=alert.id,
            budget_id=budget.id,
            period_start=alert.period_start,
            triggered_at=alert.triggered_at,
            spend_at_trigger=float(alert.spend_at_trigger),
            acknowledged=alert.acknowledged,
            budget_scope=budget.scope,
            budget_scope_value=budget.scope_value,
            budget_threshold_amount=float(budget.threshold_amount),
        )
        for alert, budget in deduped_rows
    ]
