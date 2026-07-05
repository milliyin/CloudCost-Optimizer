from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cloud_resource import CloudResource
from app.models.finding import Finding
from app.models.metric_sample import MetricSample
from app.models.user import User
from app.schemas.finding import FindingResponse


def _loads_json(payload: str) -> dict[str, Any]:
    try:
        loaded = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _build_finding(
    *,
    resource: CloudResource,
    finding_type: str,
    severity: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "resource_id": resource.resource_id,
        "resource_type": resource.resource_type,
        "finding_type": finding_type,
        "severity": severity,
        "evidence_json": json.dumps(evidence, default=str, sort_keys=True),
    }


def _network_average(metric_groups: dict[str, list[float]]) -> float:
    network_values = metric_groups.get("NetworkIn", []) + metric_groups.get("NetworkOut", [])
    if not network_values:
        return 0.0
    return float(mean(network_values))


def _detect_idle_instance(resource: CloudResource, metric_groups: dict[str, list[float]]) -> dict[str, Any] | None:
    cpu_values = metric_groups.get("CPUUtilization", [])
    if len(cpu_values) < settings.finding_min_sample_count:
        return None

    avg_cpu = float(mean(cpu_values))
    avg_network = _network_average(metric_groups)
    if avg_cpu > settings.finding_idle_cpu_threshold_percent or avg_network > settings.finding_idle_network_average_bytes:
        return None

    return _build_finding(
        resource=resource,
        finding_type="idle_instance",
        severity="critical" if avg_cpu <= 5 else "warning",
        evidence={
            "metric": "CPUUtilization",
            "avg_cpu_percent": round(avg_cpu, 2),
            "avg_network_bytes": round(avg_network, 2),
            "window_hours": settings.aws_metric_lookback_hours,
            "sample_count": len(cpu_values),
            "cpu_threshold_percent": settings.finding_idle_cpu_threshold_percent,
            "network_threshold_average_bytes": settings.finding_idle_network_average_bytes,
        },
    )


def _detect_underutilized_instance(resource: CloudResource, metric_groups: dict[str, list[float]]) -> dict[str, Any] | None:
    cpu_values = metric_groups.get("CPUUtilization", [])
    if len(cpu_values) < settings.finding_min_sample_count:
        return None

    avg_cpu = float(mean(cpu_values))
    if avg_cpu < settings.finding_idle_cpu_threshold_percent or avg_cpu >= settings.finding_underutilized_cpu_upper_percent:
        return None

    return _build_finding(
        resource=resource,
        finding_type="underutilized_instance",
        severity="warning",
        evidence={
            "metric": "CPUUtilization",
            "avg_cpu_percent": round(avg_cpu, 2),
            "window_hours": settings.aws_metric_lookback_hours,
            "sample_count": len(cpu_values),
            "lower_threshold_percent": settings.finding_idle_cpu_threshold_percent,
            "upper_threshold_percent": settings.finding_underutilized_cpu_upper_percent,
            "instance_type": resource.instance_type,
        },
    )


def _detect_oversized_mismatch(resource: CloudResource, metric_groups: dict[str, list[float]]) -> dict[str, Any] | None:
    cpu_values = metric_groups.get("CPUUtilization", [])
    if len(cpu_values) < settings.finding_min_sample_count:
        return None

    avg_cpu = float(mean(cpu_values))
    if avg_cpu < settings.finding_oversized_cpu_threshold_percent:
        return None

    return _build_finding(
        resource=resource,
        finding_type="oversized_mismatch",
        severity="critical",
        evidence={
            "metric": "CPUUtilization",
            "avg_cpu_percent": round(avg_cpu, 2),
            "max_cpu_percent": round(max(cpu_values), 2),
            "window_hours": settings.aws_metric_lookback_hours,
            "sample_count": len(cpu_values),
            "threshold_percent": settings.finding_oversized_cpu_threshold_percent,
            "instance_type": resource.instance_type,
            "note": "This is flagged as a performance risk, not pure waste.",
        },
    )


def _detect_unattached_volume(resource: CloudResource) -> dict[str, Any] | None:
    metadata = _loads_json(resource.tags_json)
    attachments = metadata.get("attachments", [])
    has_attachment = isinstance(attachments, list) and len(attachments) > 0
    if resource.resource_type != "ebs_volume" or resource.state != "available" or has_attachment:
        return None

    return _build_finding(
        resource=resource,
        finding_type="unattached_volume",
        severity="warning",
        evidence={
            "volume_state": resource.state,
            "attachment_count": len(attachments) if isinstance(attachments, list) else 0,
            "reason": "Volume is available and has no active attachments.",
        },
    )


def _detect_unused_elastic_ip(resource: CloudResource) -> dict[str, Any] | None:
    metadata = _loads_json(resource.tags_json)
    association_id = metadata.get("association_id", "")
    if resource.resource_type != "elastic_ip" or resource.state != "unassociated" or association_id:
        return None

    return _build_finding(
        resource=resource,
        finding_type="unused_elastic_ip",
        severity="warning",
        evidence={
            "allocation_id": metadata.get("allocation_id", ""),
            "association_id": association_id,
            "public_ip": metadata.get("public_ip", ""),
            "reason": "Elastic IP is allocated but not associated with a running instance.",
        },
    )


async def run_findings_detection(db: AsyncSession, organization_id: int) -> int:
    resources = (
        await db.execute(
            select(CloudResource)
            .where(CloudResource.organization_id == organization_id)
            .order_by(CloudResource.resource_type.asc(), CloudResource.resource_id.asc())
        )
    ).scalars().all()

    metric_rows = (
        await db.execute(
            select(MetricSample)
            .where(MetricSample.organization_id == organization_id)
            .order_by(MetricSample.timestamp.asc())
        )
    ).scalars().all()

    metrics_by_resource: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for sample in metric_rows:
        metrics_by_resource[sample.resource_id][sample.metric_name].append(float(sample.value))

    detected_findings: list[dict[str, Any]] = []
    for resource in resources:
        metric_groups = metrics_by_resource.get(resource.resource_id, {})
        if resource.resource_type == "ec2_instance" and resource.state == "running":
            for detector in (_detect_idle_instance, _detect_underutilized_instance, _detect_oversized_mismatch):
                finding = detector(resource, metric_groups)
                if finding is not None:
                    detected_findings.append(finding)
        elif resource.resource_type == "ebs_volume":
            finding = _detect_unattached_volume(resource)
            if finding is not None:
                detected_findings.append(finding)
        elif resource.resource_type == "elastic_ip":
            finding = _detect_unused_elastic_ip(resource)
            if finding is not None:
                detected_findings.append(finding)

    existing_findings = (
        await db.execute(select(Finding).where(Finding.organization_id == organization_id))
    ).scalars().all()
    existing_lookup = {(finding.resource_id, finding.finding_type): finding for finding in existing_findings}
    active_keys = {(item["resource_id"], item["finding_type"]) for item in detected_findings}
    now = datetime.now(UTC)

    for item in detected_findings:
        key = (item["resource_id"], item["finding_type"])
        current = existing_lookup.get(key)
        if current is None:
            db.add(
                Finding(
                    organization_id=organization_id,
                    resource_id=item["resource_id"],
                    resource_type=item["resource_type"],
                    finding_type=item["finding_type"],
                    severity=item["severity"],
                    status="open",
                    evidence_json=item["evidence_json"],
                    detected_at=now,
                    updated_at=now,
                )
            )
            continue

        current.resource_type = item["resource_type"]
        current.severity = item["severity"]
        current.status = "open"
        current.evidence_json = item["evidence_json"]
        current.detected_at = now
        current.updated_at = now

    for finding in existing_findings:
        if (finding.resource_id, finding.finding_type) not in active_keys and finding.status != "resolved":
            finding.status = "resolved"
            finding.updated_at = now

    return len(detected_findings)


async def list_findings(
    db: AsyncSession,
    current_user: User,
    *,
    finding_type: str | None,
    severity: str | None,
    status: str | None,
) -> list[FindingResponse]:
    query = select(Finding).where(Finding.organization_id == current_user.organization_id)
    if finding_type:
        query = query.where(Finding.finding_type == finding_type)
    if severity:
        query = query.where(Finding.severity == severity)
    if status:
        query = query.where(Finding.status == status)

    findings = (
        await db.execute(query.order_by(Finding.detected_at.desc(), Finding.id.desc()))
    ).scalars().all()

    return [
        FindingResponse(
            id=finding.id,
            resource_id=finding.resource_id,
            resource_type=finding.resource_type,
            finding_type=finding.finding_type,
            severity=finding.severity,
            status=finding.status,
            evidence=_loads_json(finding.evidence_json),
            detected_at=finding.detected_at,
            updated_at=finding.updated_at,
        )
        for finding in findings
    ]
