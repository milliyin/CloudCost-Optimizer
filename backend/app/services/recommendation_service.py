from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse
from app.services.audit_service import add_audit_log
from app.services.findings_service import _loads_json


def _instance_savings_floor(instance_type: str) -> float:
    lowered = (instance_type or "").lower()
    if "nano" in lowered or "micro" in lowered:
        return 8.0
    if "small" in lowered:
        return 15.0
    if "medium" in lowered:
        return 28.0
    if "large" in lowered:
        return 55.0
    if "xlarge" in lowered:
        return 95.0
    return 24.0


def _build_template(finding: Finding) -> dict[str, object]:
    evidence = _loads_json(finding.evidence_json)
    instance_type = str(evidence.get("instance_type", ""))

    if finding.finding_type == "idle_instance":
        estimate = _instance_savings_floor(instance_type)
        return {
            "action_type": "review_stop_instance",
            "description": f"Review stopping {finding.resource_id} during idle periods or replacing it with an on-demand schedule.",
            "estimated_monthly_savings": estimate,
            "explanation": (
                "Heuristic estimate based on the detected EC2 shape and current idle behavior. "
                "Approve only to mark the recommendation as reviewed; the app will not stop the instance for you."
            ),
        }
    if finding.finding_type == "underutilized_instance":
        estimate = round(_instance_savings_floor(instance_type) * 0.4, 2)
        return {
            "action_type": "review_rightsize_instance",
            "description": f"Review rightsizing {finding.resource_id} to a smaller instance family or size.",
            "estimated_monthly_savings": estimate,
            "explanation": (
                "Savings estimate assumes a smaller EC2 shape could meet the observed workload band. "
                "Use this as a planning number, not a billing-grade quote."
            ),
        }
    if finding.finding_type == "oversized_mismatch":
        return {
            "action_type": "review_scale_up_or_rearchitect",
            "description": f"Review scaling options for {finding.resource_id}; this is a performance-risk recommendation, not a cost-cut action.",
            "estimated_monthly_savings": None,
            "explanation": (
                "This recommendation is intentionally savings-neutral. The signal indicates sustained high utilization, "
                "so the safe next step is manual review rather than an automated cost reduction."
            ),
        }
    if finding.finding_type == "unattached_volume":
        return {
            "action_type": "review_delete_unattached_volume",
            "description": f"Review deleting unattached EBS volume {finding.resource_id} if it is no longer needed.",
            "estimated_monthly_savings": 5.0,
            "explanation": (
                "Estimate is a conservative placeholder for a small always-on EBS charge. "
                "Confirm backups and recovery requirements before deleting anything in AWS yourself."
            ),
        }
    if finding.finding_type == "unused_elastic_ip":
        return {
            "action_type": "review_release_unused_elastic_ip",
            "description": f"Review releasing unassociated Elastic IP {finding.resource_id} if it is no longer reserved for a near-term workload.",
            "estimated_monthly_savings": 3.5,
            "explanation": (
                "Estimate is a conservative monthly placeholder for an unused Elastic IP. "
                "Approve only to track the decision; the app will not release the address."
            ),
        }

    return {
        "action_type": "review_finding",
        "description": f"Review finding for {finding.resource_id}.",
        "estimated_monthly_savings": None,
        "explanation": "Manual review recommended.",
    }


async def sync_recommendations_from_findings(db: AsyncSession, organization_id: int) -> int:
    findings = (
        await db.execute(select(Finding).where(Finding.organization_id == organization_id))
    ).scalars().all()
    recommendations = (
        await db.execute(select(Recommendation).where(Recommendation.organization_id == organization_id))
    ).scalars().all()
    by_finding_id = {recommendation.finding_id: recommendation for recommendation in recommendations}
    created = 0

    for finding in findings:
        if finding.status == "resolved" and finding.id not in by_finding_id:
            continue

        template = _build_template(finding)
        current = by_finding_id.get(finding.id)
        if current is None:
            db.add(
                Recommendation(
                    organization_id=organization_id,
                    finding_id=finding.id,
                    action_type=str(template["action_type"]),
                    description=str(template["description"]),
                    estimated_monthly_savings=template["estimated_monthly_savings"],
                    explanation=str(template["explanation"]),
                )
            )
            created += 1
            continue

        if finding.status == "resolved" and current.status == "pending":
            current.status = "resolved"
            current.decision_reason = "Automatically closed after the underlying finding resolved in a later sync."
            current.decided_at = datetime.now(UTC)
            continue

        if finding.status == "open" and current.status == "resolved" and current.decided_by is None:
            current.status = "pending"
            current.decision_reason = ""
            current.decided_at = None

        if current.status == "pending":
            current.action_type = str(template["action_type"])
            current.description = str(template["description"])
            current.estimated_monthly_savings = template["estimated_monthly_savings"]
            current.explanation = str(template["explanation"])

    return created


async def list_recommendations(
    db: AsyncSession,
    current_user: User,
    *,
    status: str | None,
) -> list[RecommendationResponse]:
    await sync_recommendations_from_findings(db, current_user.organization_id)
    await db.commit()

    query = (
        select(Recommendation, Finding)
        .join(Finding, Finding.id == Recommendation.finding_id)
        .where(Recommendation.organization_id == current_user.organization_id)
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
    )
    if status and status != "all":
        query = query.where(Recommendation.status == status)

    rows = (await db.execute(query)).all()
    return [
        RecommendationResponse(
            id=recommendation.id,
            finding_id=finding.id,
            finding_type=finding.finding_type,
            finding_status=finding.status,
            resource_id=finding.resource_id,
            resource_type=finding.resource_type,
            severity=finding.severity,
            action_type=recommendation.action_type,
            description=recommendation.description,
            estimated_monthly_savings=float(recommendation.estimated_monthly_savings) if recommendation.estimated_monthly_savings is not None else None,
            status=recommendation.status,
            explanation=recommendation.explanation,
            decision_reason=recommendation.decision_reason,
            created_at=recommendation.created_at,
            decided_at=recommendation.decided_at,
        )
        for recommendation, finding in rows
    ]


async def decide_recommendation(
    db: AsyncSession,
    *,
    recommendation_id: int,
    current_user: User,
    status: str,
    reason: str,
) -> RecommendationResponse:
    row = (
        await db.execute(
            select(Recommendation, Finding)
            .join(Finding, Finding.id == Recommendation.finding_id)
            .where(
                Recommendation.id == recommendation_id,
                Recommendation.organization_id == current_user.organization_id,
            )
        )
    ).first()
    if row is None:
        raise ValueError("Recommendation not found")

    recommendation, finding = row
    recommendation.status = status
    recommendation.decided_by = current_user.id
    recommendation.decided_at = datetime.now(UTC)
    recommendation.decision_reason = reason.strip()

    add_audit_log(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        action=f"recommendation.{status}",
        target_type="recommendation",
        target_id=recommendation.id,
        details={
            "finding_id": finding.id,
            "finding_type": finding.finding_type,
            "resource_id": finding.resource_id,
            "reason": recommendation.decision_reason,
        },
    )
    await db.commit()
    await db.refresh(recommendation)

    return RecommendationResponse(
        id=recommendation.id,
        finding_id=finding.id,
        finding_type=finding.finding_type,
        finding_status=finding.status,
        resource_id=finding.resource_id,
        resource_type=finding.resource_type,
        severity=finding.severity,
        action_type=recommendation.action_type,
        description=recommendation.description,
        estimated_monthly_savings=float(recommendation.estimated_monthly_savings) if recommendation.estimated_monthly_savings is not None else None,
        status=recommendation.status,
        explanation=recommendation.explanation,
        decision_reason=recommendation.decision_reason,
        created_at=recommendation.created_at,
        decided_at=recommendation.decided_at,
    )
