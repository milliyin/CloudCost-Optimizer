from __future__ import annotations

import json
import math
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
                | MetricSample.resource_id.like("eipalloc-demo%")
                | MetricSample.resource_id.like("db-demo%")
                | MetricSample.resource_id.like("demo-%")
            ),
        )
    )
    await db.execute(
        delete(CloudResource).where(
            CloudResource.organization_id == organization_id,
            (
                CloudResource.resource_id.like("i-demo%")
                | CloudResource.resource_id.like("vol-demo%")
                | CloudResource.resource_id.like("eipalloc-demo%")
                | CloudResource.resource_id.like("db-demo%")
                | CloudResource.resource_id.like("demo-%")
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
    start_date = today - timedelta(days=89)
    services = [
        ("Amazon Elastic Compute Cloud - Compute", "us-east-1", "BoxUsage:t3.micro", 4.5),
        ("Amazon Relational Database Service", "us-east-1", "InstanceUsage:db.t3.micro", 2.8),
        ("Amazon Simple Storage Service", "us-east-1", "TimedStorage-ByteHrs", 1.25),
        ("AWS Lambda", "us-east-1", "Lambda-GB-Second", 0.45),
        ("Amazon CloudWatch", "us-east-1", "DataProcessing-Bytes", 0.35),
        ("Amazon DynamoDB", "us-east-1", "ReadCapacityUnit-Hrs", 0.85),
        ("Elastic Load Balancing", "us-east-1", "LCUUsage", 1.55),
        ("Amazon EC2-Container Service", "us-east-1", "Fargate-vCPU-Hours", 0.75),
    ]

    records: list[CostRecord] = []
    for offset in range(90):
        current_date = start_date + timedelta(days=offset)
        # Organic growth trend over 90 days (+20%)
        growth_trend = (offset / 89.0) * 0.95
        # Harmonic sine/cosine wave for realistic traffic cycles
        cycle_wave = math.sin(offset / 4.0) * 0.25 + math.cos(offset / 7.0) * 0.15
        # Weekend drop (SaaS usage dips on Sat/Sun)
        weekend_drop = -0.35 if current_date.weekday() >= 5 else 0.05
        # Mid-month batch processing spike on 14th-16th
        batch_spike = 0.65 if current_date.day in (14, 15, 16) else 0.0

        for index, (service, region, usage_type, baseline) in enumerate(services):
            # Apply slight service-specific multiplier variance
            service_variance = math.sin(offset / 3.0 + index) * 0.12
            amount = baseline + growth_trend + cycle_wave + weekend_drop + batch_spike + service_variance
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
            "tags": {"Name": "demo-web-idle", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
        {
            "resource_id": "i-demoapp02",
            "resource_type": "ec2_instance",
            "region": "us-east-1",
            "state": "running",
            "instance_type": "t3.small",
            "tags": {"Name": "demo-worker-underutilized", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
        {
            "resource_id": "i-demoapp03",
            "resource_type": "ec2_instance",
            "region": "us-east-1",
            "state": "running",
            "instance_type": "c5.xlarge",
            "tags": {"Name": "demo-analytics-mismatch", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
        {
            "resource_id": "vol-demo001",
            "resource_type": "ebs_volume",
            "region": "us-east-1",
            "state": "in-use",
            "instance_type": "gp3",
            "tags": {
                "Name": "demo-app-volume",
                "Environment": "demo",
                "ManagedBy": "demo-seed",
                "attachments": [{"InstanceId": "i-demoapp01", "State": "attached"}],
            },
        },
        {
            "resource_id": "vol-demo002",
            "resource_type": "ebs_volume",
            "region": "us-east-1",
            "state": "available",
            "instance_type": "gp2",
            "tags": {
                "Name": "demo-unattached-backup-volume",
                "Environment": "demo",
                "ManagedBy": "demo-seed",
                "attachments": [],
            },
        },
        {
            "resource_id": "eipalloc-demo001",
            "resource_type": "elastic_ip",
            "region": "us-east-1",
            "state": "unassociated",
            "instance_type": "",
            "tags": {
                "Name": "demo-unassociated-eip",
                "Environment": "demo",
                "ManagedBy": "demo-seed",
                "public_ip": "54.210.12.99",
                "allocation_id": "eipalloc-demo001",
                "association_id": "",
            },
        },
        {
            "resource_id": "db-demo-postgres",
            "resource_type": "rds_instance",
            "region": "us-east-1",
            "state": "available",
            "instance_type": "db.t3.micro",
            "tags": {"Name": "demo-postgres", "Environment": "demo", "ManagedBy": "demo-seed"},
        },
        {
            "resource_id": "demo-analytics-bucket",
            "resource_type": "s3_bucket",
            "region": "us-east-1",
            "state": "active",
            "instance_type": "",
            "tags": {"Name": "demo-analytics-bucket", "Environment": "demo", "ManagedBy": "demo-seed"},
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
        # i-demoapp01: Idle instance (CPU < 5%, low network)
        ("i-demoapp01", "CPUUtilization", [3.2, 3.8, 3.5, 4.1]),
        ("i-demoapp01", "NetworkIn", [150.0, 180.0, 160.0, 170.0]),
        ("i-demoapp01", "NetworkOut", [120.0, 140.0, 130.0, 135.0]),
        # i-demoapp02: Underutilized instance (CPU 15-20%)
        ("i-demoapp02", "CPUUtilization", [16.5, 18.2, 17.1, 19.0]),
        ("i-demoapp02", "NetworkIn", [450.0, 520.0, 480.0, 500.0]),
        ("i-demoapp02", "NetworkOut", [380.0, 410.0, 390.0, 420.0]),
        # i-demoapp03: Oversized mismatch (CPU 88-95%)
        ("i-demoapp03", "CPUUtilization", [89.5, 92.3, 91.0, 94.8]),
        ("i-demoapp03", "NetworkIn", [2500.0, 2800.0, 2600.0, 2750.0]),
        ("i-demoapp03", "NetworkOut", [2100.0, 2400.0, 2300.0, 2350.0]),
    ]
    timestamps = [now - timedelta(hours=3), now - timedelta(hours=2), now - timedelta(hours=1), now]

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


async def remove_demo_seed(db: AsyncSession, current_user: User) -> None:
    organization_id = current_user.organization_id
    await clear_workspace_for_demo_seed(db, organization_id)
    await db.commit()
