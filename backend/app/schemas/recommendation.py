from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationDecisionRequest(BaseModel):
    reason: str = Field(default="", max_length=2000)


class RecommendationRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class RecommendationResponse(BaseModel):
    id: int
    finding_id: int
    finding_type: str
    finding_status: str
    resource_id: str
    resource_type: str
    severity: str
    action_type: str
    description: str
    estimated_monthly_savings: float | None
    status: str
    explanation: str
    decision_reason: str
    created_at: datetime
    decided_at: datetime | None

