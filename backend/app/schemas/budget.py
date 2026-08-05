from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class BudgetRequest(BaseModel):
    scope: str = Field(pattern="^(total|service)$")
    scope_value: str = Field(default="", max_length=255)
    threshold_amount: float = Field(gt=0)
    period: str = Field(default="monthly", pattern="^monthly$")

    @field_validator("scope_value")
    @classmethod
    def validate_scope_value(cls, value: str, info) -> str:
        scope = info.data.get("scope")
        if scope == "service" and not value.strip():
            raise ValueError("scope_value is required for service budgets")
        return value.strip()


class BudgetResponse(BaseModel):
    id: int
    scope: str
    scope_value: str
    threshold_amount: float
    period: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AlertResponse(BaseModel):
    id: int
    budget_id: int
    period_start: date
    triggered_at: datetime
    spend_at_trigger: float
    acknowledged: bool
    budget_scope: str
    budget_scope_value: str
    budget_threshold_amount: float
