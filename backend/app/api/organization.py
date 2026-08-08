from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user, require_role
from app.models.aws_connection import AWSConnection
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.organization import (
    AWSConnectionRequest,
    AWSConnectionStatusResponse,
    DemoSeedResponse,
    DemoSeedSummaryResponse,
    OrganizationContextResponse,
)
from app.services.crypto import encrypt_secret
from app.services.demo_seed import remove_demo_seed, seed_demo_workspace

router = APIRouter(prefix="/organization", tags=["organization"])


@router.get("/me", response_model=OrganizationContextResponse)
async def get_organization_context(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> OrganizationContextResponse:
    organization = await db.get(Organization, current_user.organization_id)
    connection = await db.scalar(select(AWSConnection).where(AWSConnection.organization_id == current_user.organization_id))
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return OrganizationContextResponse(
        organization=organization,
        aws_connection=AWSConnectionStatusResponse(
            has_connection=connection is not None,
            region=connection.region if connection else None,
        ),
    )


@router.put("/aws-connection", response_model=OrganizationContextResponse)
async def save_organization_aws_connection(
    payload: AWSConnectionRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> OrganizationContextResponse:
    organization = await db.get(Organization, current_user.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    connection = await db.scalar(select(AWSConnection).where(AWSConnection.organization_id == current_user.organization_id))
    if connection is None:
        connection = AWSConnection(
            organization_id=current_user.organization_id,
            access_key_id_encrypted=encrypt_secret(payload.access_key_id),
            secret_access_key_encrypted=encrypt_secret(payload.secret_access_key),
            region=payload.region,
        )
        db.add(connection)
    else:
        connection.access_key_id_encrypted = encrypt_secret(payload.access_key_id)
        connection.secret_access_key_encrypted = encrypt_secret(payload.secret_access_key)
        connection.region = payload.region

    await db.commit()
    return OrganizationContextResponse(
        organization=organization,
        aws_connection=AWSConnectionStatusResponse(has_connection=True, region=payload.region),
    )


@router.post("/demo-seed", response_model=DemoSeedResponse)
async def seed_organization_demo_workspace(
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> DemoSeedResponse:
    summary = await seed_demo_workspace(db, current_user)
    return DemoSeedResponse(
        message=(
            "Demo workspace loaded for this organization. "
            "The saved AWS connection was cleared and the dashboard now uses simulated data."
            if summary.aws_connection_removed
            else "Demo workspace loaded for this organization with simulated data."
        ),
        summary=DemoSeedSummaryResponse(
            cost_records_seeded=summary.cost_records_seeded,
            resources_seeded=summary.resources_seeded,
            metric_samples_seeded=summary.metric_samples_seeded,
            aws_connection_removed=summary.aws_connection_removed,
        ),
    )


@router.post("/demo-clear")
async def clear_organization_demo_workspace(
    db: DbSession,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> dict[str, str]:
    await remove_demo_seed(db, current_user)
    return {"message": "Demo data successfully removed from this workspace."}
