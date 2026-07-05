from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class AWSConnectionRequest(BaseModel):
    access_key_id: str = Field(min_length=16, max_length=128)
    secret_access_key: str = Field(min_length=20, max_length=256)
    region: str = Field(min_length=4, max_length=64)


class AWSConnectionStatusResponse(BaseModel):
    has_connection: bool
    region: str | None = None


class OrganizationContextResponse(BaseModel):
    organization: OrganizationResponse
    aws_connection: AWSConnectionStatusResponse


class DemoSeedSummaryResponse(BaseModel):
    cost_records_seeded: int
    resources_seeded: int
    metric_samples_seeded: int
    aws_connection_removed: bool


class DemoSeedResponse(BaseModel):
    message: str
    summary: DemoSeedSummaryResponse
