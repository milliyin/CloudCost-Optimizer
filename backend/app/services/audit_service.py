from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


def add_audit_log(
    db: AsyncSession,
    *,
    actor: User | None,
    organization_id: int,
    action: str,
    target_type: str,
    target_id: int,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=actor.id if actor else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=json.dumps(details or {}, default=str, sort_keys=True),
        )
    )
