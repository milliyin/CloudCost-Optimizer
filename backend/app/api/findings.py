from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.finding import FindingResponse
from app.services.findings_service import list_findings

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=list[FindingResponse])
async def read_findings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    finding_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default="open"),
) -> list[FindingResponse]:
    return await list_findings(
        db,
        current_user,
        finding_type=finding_type,
        severity=severity,
        status=status,
    )
