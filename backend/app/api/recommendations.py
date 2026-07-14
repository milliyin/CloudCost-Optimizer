from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.recommendation import (
    RecommendationDecisionRequest,
    RecommendationRejectRequest,
    RecommendationResponse,
)
from app.services.recommendation_service import decide_recommendation, list_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationResponse])
async def read_recommendations(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    status: str | None = Query(default="all"),
) -> list[RecommendationResponse]:
    return await list_recommendations(db, current_user, status=status)


@router.post("/{recommendation_id}/approve", response_model=RecommendationResponse)
async def approve_recommendation(
    recommendation_id: int,
    payload: RecommendationDecisionRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> RecommendationResponse:
    try:
        return await decide_recommendation(
            db,
            recommendation_id=recommendation_id,
            current_user=current_user,
            status="approved",
            reason=payload.reason,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{recommendation_id}/reject", response_model=RecommendationResponse)
async def reject_recommendation(
    recommendation_id: int,
    payload: RecommendationRejectRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> RecommendationResponse:
    try:
        return await decide_recommendation(
            db,
            recommendation_id=recommendation_id,
            current_user=current_user,
            status="rejected",
            reason=payload.reason,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
