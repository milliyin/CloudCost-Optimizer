from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CostRecord(Base):
    __tablename__ = "cost_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "date",
            "service",
            "region",
            "usage_type",
            "account_id",
            name="uq_cost_records_natural_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    service: Mapped[str] = mapped_column(String(255), default="", server_default="")
    region: Mapped[str] = mapped_column(String(255), default="", server_default="")
    amount: Mapped[float] = mapped_column(Numeric(12, 4))
    currency: Mapped[str] = mapped_column(String(16))
    usage_type: Mapped[str] = mapped_column(String(255), default="", server_default="")
    account_id: Mapped[str] = mapped_column(String(64), default="", server_default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
