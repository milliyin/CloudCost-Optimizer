from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud_resource import CloudResource
from app.models.cost_record import CostRecord
from app.models.metric_sample import MetricSample
from app.models.user import User
from app.schemas.dashboard import CostGroupResponse, ResourceRowResponse, SpendSummaryResponse, TrendPointResponse


def _resolve_date_range(start: date | None, end: date | None) -> tuple[date, date]:
    today = date.today()
    resolved_end = end or today
    resolved_start = start or (resolved_end - timedelta(days=29))
    return resolved_start, resolved_end


async def get_spend_summary(db: AsyncSession, current_user: User) -> SpendSummaryResponse:
    today = date.today()
    current_month_start = today.replace(day=1)
    prior_month_end = current_month_start - timedelta(days=1)
    prior_month_start = prior_month_end.replace(day=1)

    summary_rows = (
        await db.execute(
            select(
                CostRecord.date,
                func.sum(CostRecord.amount).label("amount"),
                func.min(CostRecord.currency).label("currency"),
            )
            .where(
                CostRecord.organization_id == current_user.organization_id,
                CostRecord.date >= prior_month_start,
                CostRecord.date <= today,
            )
            .group_by(CostRecord.date)
        )
    ).all()

    current_month_spend = 0.0
    prior_month_spend = 0.0
    currency = "USD"
    for row in summary_rows:
        currency = row.currency or currency
        if row.date >= current_month_start:
            current_month_spend += float(row.amount or 0)
        else:
            prior_month_spend += float(row.amount or 0)

    top_service_row = (
        await db.execute(
            select(CostRecord.service, func.sum(CostRecord.amount).label("amount"))
            .where(
                CostRecord.organization_id == current_user.organization_id,
                CostRecord.date >= current_month_start,
                CostRecord.date <= today,
                CostRecord.service != "",
            )
            .group_by(CostRecord.service)
            .order_by(func.sum(CostRecord.amount).desc())
            .limit(1)
        )
    ).first()

    percent_change = None
    if prior_month_spend > 0:
        percent_change = ((current_month_spend - prior_month_spend) / prior_month_spend) * 100

    return SpendSummaryResponse(
        current_month_spend=current_month_spend,
        prior_month_spend=prior_month_spend,
        percent_change=percent_change,
        top_service=top_service_row.service if top_service_row else None,
        currency=currency,
    )


async def get_cost_groups(
    db: AsyncSession,
    current_user: User,
    *,
    dimension: str,
    start: date | None,
    end: date | None,
) -> list[CostGroupResponse]:
    resolved_start, resolved_end = _resolve_date_range(start, end)
    column = CostRecord.service if dimension == "service" else CostRecord.region

    rows = (
        await db.execute(
            select(column.label("key"), func.sum(CostRecord.amount).label("amount"), func.min(CostRecord.currency).label("currency"))
            .where(
                CostRecord.organization_id == current_user.organization_id,
                CostRecord.date >= resolved_start,
                CostRecord.date <= resolved_end,
                column != "",
            )
            .group_by(column)
            .order_by(func.sum(CostRecord.amount).desc())
        )
    ).all()

    return [
        CostGroupResponse(
            key=row.key,
            amount=float(row.amount or 0),
            currency=row.currency or "USD",
        )
        for row in rows
    ]


async def get_spend_trend(
    db: AsyncSession,
    current_user: User,
    *,
    start: date | None,
    end: date | None,
    granularity: str,
) -> list[TrendPointResponse]:
    resolved_start, resolved_end = _resolve_date_range(start, end)
    rows = (
        await db.execute(
            select(CostRecord.date, func.sum(CostRecord.amount).label("amount"), func.min(CostRecord.currency).label("currency"))
            .where(
                CostRecord.organization_id == current_user.organization_id,
                CostRecord.date >= resolved_start,
                CostRecord.date <= resolved_end,
            )
            .group_by(CostRecord.date)
            .order_by(CostRecord.date.asc())
        )
    ).all()

    if granularity == "monthly":
        monthly_buckets: dict[date, dict] = defaultdict(lambda: {"amount": 0.0, "currency": "USD"})
        for row in rows:
            month_start = row.date.replace(day=1)
            monthly_buckets[month_start]["amount"] += float(row.amount or 0)
            monthly_buckets[month_start]["currency"] = row.currency or "USD"
        return [
            TrendPointResponse(period_start=period_start, amount=data["amount"], currency=data["currency"])
            for period_start, data in sorted(monthly_buckets.items())
        ]

    return [
        TrendPointResponse(
            period_start=row.date,
            amount=float(row.amount or 0),
            currency=row.currency or "USD",
        )
        for row in rows
    ]


async def get_resource_inventory_rows(db: AsyncSession, current_user: User) -> list[ResourceRowResponse]:
    resources = (
        await db.execute(
            select(CloudResource)
            .where(CloudResource.organization_id == current_user.organization_id)
            .order_by(CloudResource.last_seen.desc())
        )
    ).scalars().all()

    latest_metrics = (
        await db.execute(
            select(
                MetricSample.resource_id,
                MetricSample.metric_name,
                func.max(MetricSample.timestamp).label("latest_timestamp"),
            )
            .where(MetricSample.organization_id == current_user.organization_id)
            .group_by(MetricSample.resource_id, MetricSample.metric_name)
        )
    ).all()

    metric_lookup: dict[tuple[str, str], float] = {}
    for row in latest_metrics:
        metric_value_row = (
            await db.execute(
                select(MetricSample.value)
                .where(
                    and_(
                        MetricSample.organization_id == current_user.organization_id,
                        MetricSample.resource_id == row.resource_id,
                        MetricSample.metric_name == row.metric_name,
                        MetricSample.timestamp == row.latest_timestamp,
                    )
                )
            )
        ).first()
        if metric_value_row is not None:
            metric_lookup[(row.resource_id, row.metric_name)] = float(metric_value_row.value)

    return [
        ResourceRowResponse(
            resource_id=resource.resource_id,
            resource_type=resource.resource_type,
            region=resource.region,
            state=resource.state,
            instance_type=resource.instance_type,
            last_seen=resource.last_seen,
            latest_cpu_utilization=metric_lookup.get((resource.resource_id, "CPUUtilization")),
            latest_network_in=metric_lookup.get((resource.resource_id, "NetworkIn")),
            latest_network_out=metric_lookup.get((resource.resource_id, "NetworkOut")),
        )
        for resource in resources
    ]
