from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("budget_id", "period_start", name="uq_alerts_budget_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id", ondelete="CASCADE"), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    spend_at_trigger: Mapped[float] = mapped_column(Numeric(12, 2))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)

