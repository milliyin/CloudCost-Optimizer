from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cloud_resource import CloudResource
from app.models.cost_record import CostRecord
from app.models.metric_sample import MetricSample
from app.models.organization import Organization
from app.services.aws.cloudwatch_metrics import get_instance_metric_samples
from app.services.aws.credentials import get_organization_aws_credentials
from app.services.aws.cost_explorer import get_cost_forecast, get_cost_grouped_by_region, get_cost_grouped_by_service
from app.services.aws.errors import AWSServiceError
from app.services.aws.resource_inventory import get_resource_inventory
from app.services.demo_seed import clear_demo_seed_workspace


async def _upsert_cost_records(db: AsyncSession, payloads: list[dict], synced_at: datetime, organization_id: int) -> int:
    if not payloads:
        return 0

    values = [
        {
            **payload,
            "organization_id": organization_id,
            "amount": Decimal(str(payload["amount"])),
            "synced_at": synced_at,
        }
        for payload in payloads
    ]
    statement = insert(CostRecord).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_cost_records_natural_key",
        set_={
            "amount": statement.excluded.amount,
            "currency": statement.excluded.currency,
            "synced_at": statement.excluded.synced_at,
        },
    )
    await db.execute(statement)
    return len(values)


async def _upsert_resources(db: AsyncSession, payloads: list[dict], organization_id: int) -> int:
    if not payloads:
        return 0

    values = [{**payload, "organization_id": organization_id} for payload in payloads]
    statement = insert(CloudResource).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_cloud_resources_identity",
        set_={
            "region": statement.excluded.region,
            "state": statement.excluded.state,
            "instance_type": statement.excluded.instance_type,
            "tags_json": statement.excluded.tags_json,
            "last_seen": statement.excluded.last_seen,
        },
    )
    await db.execute(statement)
    return len(values)


async def _upsert_metric_samples(db: AsyncSession, payloads: list[dict], organization_id: int) -> int:
    if not payloads:
        return 0

    values = [{**payload, "organization_id": organization_id} for payload in payloads]
    statement = insert(MetricSample).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_metric_samples_identity",
        set_={
            "value": statement.excluded.value,
            "unit": statement.excluded.unit,
        },
    )
    await db.execute(statement)
    return len(values)


async def run_sync(db: AsyncSession, organization: Organization) -> dict:
    synced_at = datetime.now(UTC)
    await clear_demo_seed_workspace(db, organization.id)
    credentials = await get_organization_aws_credentials(db, organization.id)
    summary = {
        "organization_id": organization.id,
        "organization_name": organization.name,
        "cost_records_synced": 0,
        "resources_synced": 0,
        "metric_samples_synced": 0,
        "forecast_points": 0,
        "warnings": [],
    }

    if credentials is None:
        summary["warnings"].append(
            "No AWS connection is configured for this organization yet. Save organization-specific AWS credentials before running sync."
        )
        await db.commit()
        return summary

    try:
        service_costs = get_cost_grouped_by_service(settings.aws_cost_lookback_days, credentials)
        region_costs = get_cost_grouped_by_region(settings.aws_cost_lookback_days, credentials)
        forecast = get_cost_forecast(credentials)
    except AWSServiceError as error:
        if error.service == "Cost Explorer":
            summary["warnings"].append(str(error))
            service_costs = []
            region_costs = []
            forecast = {"ForecastResultsByTime": []}
        else:
            raise

    inventory, inventory_warnings = get_resource_inventory(credentials)
    summary["warnings"].extend(inventory_warnings)
    ec2_instance_ids = [resource["resource_id"] for resource in inventory if resource["resource_type"] == "ec2_instance"]

    metric_samples: list[dict] = []
    for instance_id in ec2_instance_ids:
        try:
            metric_samples.extend(get_instance_metric_samples(instance_id, credentials))
        except AWSServiceError as error:
            summary["warnings"].append(f"{instance_id}: {error}")

    summary["cost_records_synced"] += await _upsert_cost_records(db, service_costs, synced_at, organization.id)
    summary["cost_records_synced"] += await _upsert_cost_records(db, region_costs, synced_at, organization.id)
    summary["resources_synced"] = await _upsert_resources(db, inventory, organization.id)
    summary["metric_samples_synced"] = await _upsert_metric_samples(db, metric_samples, organization.id)
    summary["forecast_points"] = len(forecast.get("ForecastResultsByTime", []))

    await db.commit()
    return summary
