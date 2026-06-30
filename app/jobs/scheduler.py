from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.jobs.check_lists import estimate_from_live


def build_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_scheduled_check,
        CronTrigger(minute=0, hour="*/2", timezone=settings.timezone),
        args=[settings],
        id="rgrtu_check",
        max_instances=1,
        replace_existing=True,
    )
    return scheduler


async def run_scheduled_check(settings: Settings) -> None:
    await estimate_from_live(settings.total_default_score, settings)
