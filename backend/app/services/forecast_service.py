from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.cost_record import CostRecord
from app.models.user import User
from app.ml.forecaster import ForecastResult, train_and_forecast_service
from app.schemas.budget import BudgetResponse


async def get_service_forecast(
    db: AsyncSession,
    current_user: User,
    service_filter: str | None = None,
    horizon_days: int = 30,
) -> dict[str, Any]:
    organization_id = current_user.organization_id

    cost_records = (
        await db.execute(
            select(CostRecord)
            .where(CostRecord.organization_id == organization_id)
            .order_by(CostRecord.date.asc())
        )
    ).scalars().all()

    result: ForecastResult = train_and_forecast_service(
        cost_records=list(cost_records),
        service_filter=service_filter,
        horizon_days=horizon_days,
    )

    # Check proactive budget breach warning
    budgets = (
        await db.execute(
            select(Budget).where(Budget.organization_id == organization_id)
        )
    ).scalars().all()

    proactive_warnings = []
    today = date.today()
    current_month_start = today.replace(day=1)

    # Sum current month spend so far
    current_month_actual = sum(
        float(r.amount)
        for r in cost_records
        if r.date >= current_month_start and (not service_filter or service_filter == "total" or r.service == service_filter)
    )

    cumulative = current_month_actual
    breach_date = None

    for f in result.forecast:
        f_date = datetime.strptime(f["date"], "%Y-%m-%d").date()
        if f_date.month == today.month:
            cumulative += f["amount"]
            for b in budgets:
                if b.scope == "total" or (b.scope == "service" and b.scope_value == service_filter):
                    if cumulative >= float(b.threshold_amount) and not breach_date:
                        breach_date = f["date"]
                        proactive_warnings.append(
                            {
                                "budget_id": b.id,
                                "scope": b.scope,
                                "scope_value": b.scope_value,
                                "threshold_amount": float(b.threshold_amount),
                                "projected_month_end": round(cumulative, 2),
                                "projected_breach_date": breach_date,
                                "message": f"Projected monthly spend (${round(cumulative, 2):.2f}) is forecasted to breach your {b.scope} budget threshold (${float(b.threshold_amount):.2f}) on {breach_date}.",
                            }
                        )

    # 1. Projected current month total (actual spend so far + forecast for rest of month)
    projected_current_month_total = current_month_actual + sum(
        f["amount"]
        for f in result.forecast
        if datetime.strptime(f["date"], "%Y-%m-%d").date().month == today.month
    )

    # 2. Next 30-day predicted total (sum of 30-day forecast horizon)
    next_30d_expected_total = sum(
        f["amount"] for f in result.forecast[:30]
    )

    # 3. Next monthly expected total (30-day projected spend)
    projected_next_month_total = next_30d_expected_total

    return {
        "service": result.service,
        "model_name": result.model_name,
        "mae": result.mae,
        "rmse": result.rmse,
        "baseline_mae": result.baseline_mae,
        "baseline_rmse": result.baseline_rmse,
        "horizon_days": result.horizon_days,
        "data_points": result.data_points,
        "limited_history_note": result.limited_history_note,
        "projected_current_month_total": round(projected_current_month_total, 2),
        "next_30d_expected_total": round(next_30d_expected_total, 2),
        "projected_next_month_total": round(projected_next_month_total, 2),
        "historical": result.historical,
        "forecast": result.forecast,
        "proactive_warnings": proactive_warnings,
    }
