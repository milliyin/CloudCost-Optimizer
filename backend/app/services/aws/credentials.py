from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.aws_connection import AWSConnection
from app.models.organization import Organization
from app.services.crypto import decrypt_secret


@dataclass
class AWSCredentials:
    access_key_id: str
    secret_access_key: str
    region: str


def _has_global_aws_config() -> bool:
    return (
        settings.aws_access_key_id != "replace-with-your-aws-access-key-id"
        and settings.aws_secret_access_key != "replace-with-your-aws-secret-access-key"
    )


async def get_organization_aws_credentials(db: AsyncSession, organization_id: int) -> AWSCredentials | None:
    connection = await db.scalar(select(AWSConnection).where(AWSConnection.organization_id == organization_id))
    if connection is not None:
        return AWSCredentials(
            access_key_id=decrypt_secret(connection.access_key_id_encrypted),
            secret_access_key=decrypt_secret(connection.secret_access_key_encrypted),
            region=connection.region,
        )

    organization = await db.get(Organization, organization_id)
    if not _has_global_aws_config() or organization is None or organization.name != "Legacy Default Organization":
        return None

    return AWSCredentials(
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
        region=settings.aws_region,
    )
