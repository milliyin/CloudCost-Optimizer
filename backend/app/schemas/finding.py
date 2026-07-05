from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FindingResponse(BaseModel):
    id: int
    resource_id: str
    resource_type: str
    finding_type: str
    severity: str
    status: str
    evidence: dict[str, Any]
    detected_at: datetime
    updated_at: datetime
