from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AWSConnection(Base):
    __tablename__ = "aws_connections"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_aws_connections_organization"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    access_key_id_encrypted: Mapped[str] = mapped_column(String(1024))
    secret_access_key_encrypted: Mapped[str] = mapped_column(String(1024))
    region: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
