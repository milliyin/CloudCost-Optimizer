from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, require_role
from app.models.user import User, UserRole
from app.services.aws.errors import AWSServiceError
from app.services.sync_service import run_sync

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/run", response_model=dict)
async def run_sync_now(
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> dict:
    try:
        summary = await run_sync(db)
    except AWSServiceError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": str(error),
                "code": error.code,
                "service": error.service,
            },
        ) from error

    return {
        "message": f"Sync completed for {current_user.email}",
        "summary": summary,
    }
