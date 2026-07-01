from datetime import date, datetime

from pydantic import BaseModel


class SpendSummaryResponse(BaseModel):
    current_month_spend: float
    prior_month_spend: float
    percent_change: float | None
    top_service: str | None
    currency: str


class CostGroupResponse(BaseModel):
    key: str
    amount: float
    currency: str


class TrendPointResponse(BaseModel):
    period_start: date
    amount: float
    currency: str


class ResourceRowResponse(BaseModel):
    resource_id: str
    resource_type: str
    region: str
    state: str
    instance_type: str
    last_seen: datetime
    latest_cpu_utilization: float | None = None
    latest_network_in: float | None = None
    latest_network_out: float | None = None

