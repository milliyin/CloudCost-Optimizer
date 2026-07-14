from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aws_connection import AWSConnection
from app.models.cloud_resource import CloudResource
from app.models.cost_record import CostRecord
from app.models.finding import Finding
from app.models.metric_sample import MetricSample
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.findings_service import run_findings_detection
from app.services.recommendation_service import sync_recommendations_from_findings


@dataclass
class DemoSeedSummary:
    cost_records_seeded: int
    resources_seeded: int
    metric_samples_seeded: int
    aws_connection_removed: bool


def _demo_account_id(organization_id: int) -> str:
    return f"demo-org-{organization_id}"


async def clear_demo_seed_workspace(db: AsyncSession, organization_id: int) -> None:
    await db.execute(
        delete(MetricSample).where(
            MetricSample.organization_id == organization_id,
            (
                MetricSample.resource_id.like("i-demo%")
                | MetricSample.resource_id.like("vol-demo%")
                | MetricSample.resource_id.like("db-demo%")
            ),
        )
    )
    await db.execute(
        delete(CloudResource).where(
            CloudResource.organization_id == organization_id,
            (
                CloudResource.resource_id.like("i-demo%")
                | CloudResource.resource_id.like("vol-demo%")
                | CloudResource.resource_id.like("db-demo%")
                | CloudResource.tags_json.like("%demo-seed%")
            ),
        )
    )
    await db.execute(
        delete(CostRecord).where(
            CostRecord.organization_id == organization_id,
            CostRecord.account_id == _demo_account_id(organization_id),
        )
    )


async def clear_workspace_for_demo_seed(db: AsyncSession, organization_id: int) -> None:
    await db.execute(delete(Recommendation).where(Recommendation.organization_id == organization_id))
    await db.execute(delete(Finding).where(Finding.organization_id == organization_id))
    await db.execute(delete(MetricSample).where(MetricSample.organization_id == organization_id))
    await db.execute(delete(CloudResource).where(CloudResource.organization_id == organization_id))
    await db.execute(delete(CostRecord).where(CostRecord.organization_id == organization_id))


def _build_cost_records(organization_id: int, today: date) -> list[CostRecord]:
    start_date = today - timedelta(days=44)
    services = [
        ("Amazon Elastic Compute Cloud - Compute", "us-east-1", "BoxUsage:t3.micro", 2.8),
        ("Amazon Relational Database Service", "us-east-1", "InstanceUsage:db.t3.micro", 1.9),
        ("Amazon Simple Storage Service", "us-east-1", "TimedStorage-ByteHrs", 0.75),
        ("AWS Lambda", "us-east-1", "Lambda-GB-Second", 0.35),
    ]

    records: list[CostRecord] = []
    for offset in range(45):
        current_date = start_date + timedelta(days=offset)
        wave = (offset % 7) * 0.14
        weekend_discount = -0.22 if current_date.weekday() >= 5 else 0
        for index, (service, region, usage_type, baseline) in enumerate(services):
            amount = baseline + wave + (index * 0.11) + weekend_discount
            records.append(
                CostRecord(
                    organization_id=organization_id,
                    date=current_date,
                    service=service,
                    region=region,
                    amount=round(max(amount, 0.08), 4),
                    currency="USD",
                    usage_type=usage_type,
                    account_id=_demo_account_id(organization_id),
                )
            )
    return records


def _build_resource_records(organization_id: int, now: datetime) -> list[CloudResource]:
    resources = [
        {
            "resource_id": "i-demoapp01",
            "resource_type": "ec2_instance",
            "region": "us-east-1",
            "state": "running",
            "instance_type": "t3.micro",
            "tags": {"Name": "demo-web-1", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
        {
            "resource_id": "i-demoapp02",
            "resource_type": "ec2_instance",
            "region": "us-east-1",
            "state": "running",
            "instance_type": "t3.small",
            "tags": {"Name": "demo-worker-1", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
        {
            "resource_id": "vol-demo001",
            "resource_type": "ebs_volume",
            "region": "us-east-1",
            "state": "in-use",
            "instance_type": "",
            "tags": {"Name": "demo-app-volume", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
        {
            "resource_id": "db-demo-postgres",
            "resource_type": "rds_instance",
            "region": "us-east-1",
            "state": "available",
            "instance_type": "db.t3.micro",
            "tags": {"Name": "demo-postgres", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
    ]

    return [
        CloudResource(
            organization_id=organization_id,
            resource_id=resource["resource_id"],
            resource_type=resource["resource_type"],
            region=resource["region"],
            state=resource["state"],
            instance_type=resource["instance_type"],
            tags_json=json.dumps(resource["tags"]),
            last_seen=now,
        )
        for resource in resources
    ]


def _build_metric_samples(organization_id: int, now: datetime) -> list[MetricSample]:
    metric_points = [
        ("i-demoapp01", "CPUUtilization", [11.8, 16.2, 14.9]),
        ("i-demoapp01", "NetworkIn", [182.4, 221.1, 205.7]),
        ("i-demoapp01", "NetworkOut", [145.3, 176.8, 168.2]),
        ("i-demoapp02", "CPUUtilization", [28.2, 34.5, 31.1]),
        ("i-demoapp02", "NetworkIn", [91.6, 104.7, 112.2]),
        ("i-demoapp02", "NetworkOut", [120.5, 139.1, 133.4]),
    ]
    timestamps = [now - timedelta(hours=2), now - timedelta(hours=1), now]

    samples: list[MetricSample] = []
    for resource_id, metric_name, values in metric_points:
        unit = "%" if metric_name == "CPUUtilization" else "Bytes"
        for timestamp, value in zip(timestamps, values, strict=True):
            samples.append(
                MetricSample(
                    organization_id=organization_id,
                    resource_id=resource_id,
                    metric_name=metric_name,
                    timestamp=timestamp,
                    value=value,
                    unit=unit,
                )
            )
    return samples


async def seed_demo_workspace(db: AsyncSession, current_user: User) -> DemoSeedSummary:
    organization_id = current_user.organization_id
    existing_connection = await db.scalar(
        select(AWSConnection).where(AWSConnection.organization_id == organization_id)
    )

    await clear_workspace_for_demo_seed(db, organization_id)

    aws_connection_removed = False
    if existing_connection is not None:
        await db.delete(existing_connection)
        aws_connection_removed = True

    now = datetime.combine(date.today(), time(12, 0), tzinfo=timezone.utc)
    cost_records = _build_cost_records(organization_id, now.date())
    resource_records = _build_resource_records(organization_id, now)
    metric_samples = _build_metric_samples(organization_id, now)

    db.add_all(cost_records)
    db.add_all(resource_records)
    db.add_all(metric_samples)
    await db.flush()
    await run_findings_detection(db, organization_id)
    await sync_recommendations_from_findings(db, organization_id)
    await db.commit()

    return DemoSeedSummary(
        cost_records_seeded=len(cost_records),
        resources_seeded=len(resource_records),
        metric_samples_seeded=len(metric_samples),
        aws_connection_removed=aws_connection_removed,
    )
