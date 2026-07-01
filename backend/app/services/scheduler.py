from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.services.sync_service import run_sync

scheduler = AsyncIOScheduler()


async def scheduled_sync_job() -> None:
    async with SessionLocal() as session:
        organizations = (await session.scalars(select(Organization))).all()
        for organization in organizations:
            await run_sync(session, organization)


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        scheduled_sync_job,
        "interval",
        hours=settings.aws_sync_interval_hours,
        id="aws-sync-job",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
