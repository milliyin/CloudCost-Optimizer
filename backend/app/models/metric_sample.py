from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MetricSample(Base):
    __tablename__ = "metric_samples"
    __table_args__ = (
        UniqueConstraint("resource_id", "metric_name", "timestamp", name="uq_metric_samples_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resource_id: Mapped[str] = mapped_column(String(255), index=True)
    metric_name: Mapped[str] = mapped_column(String(128), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(64), default="", server_default="")
