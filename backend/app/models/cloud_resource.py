from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CloudResource(Base):
    __tablename__ = "cloud_resources"
    __table_args__ = (
        UniqueConstraint("resource_id", "resource_type", name="uq_cloud_resources_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resource_id: Mapped[str] = mapped_column(String(255), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(64), default="", server_default="")
    state: Mapped[str] = mapped_column(String(64), default="", server_default="")
    instance_type: Mapped[str] = mapped_column(String(128), default="", server_default="")
    tags_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
