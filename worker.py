import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from accountant_bot.bot.runtime import build_bot
from accountant_bot.core.config import get_settings
from accountant_bot.core.logging import configure_logging
from accountant_bot.jobs.tasks import deliver_law_updates, send_due_reminders, sync_ozon_connections, sync_user_events


logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    bot = build_bot(settings) if settings.telegram_bot_configured else None

    scheduler.add_job(
        sync_ozon_connections,
        "interval",
        id="ozon_sync",
        minutes=settings.ozon_sync_interval_minutes,
        kwargs={"limit": settings.ozon_sync_batch_limit},
        coalesce=True,
        max_instances=1,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        sync_user_events,
        "cron",
        id="sync_user_events",
        hour=settings.user_event_sync_hour,
        minute=0,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    if bot is not None:
        scheduler.add_job(
            send_due_reminders,
            "interval",
            id="send_due_reminders",
            minutes=settings.reminder_dispatch_interval_minutes,
            kwargs={"bot": bot, "batch_size": settings.reminder_batch_size},
            coalesce=True,
            max_instances=1,
            misfire_grace_time=120,
        )
        scheduler.add_job(
            deliver_law_updates,
            "interval",
            id="deliver_law_updates",
            minutes=settings.law_fetch_interval_minutes,
            kwargs={"bot": bot, "min_importance": settings.law_min_importance_score},
            coalesce=True,
            max_instances=1,
            misfire_grace_time=120,
        )
    else:
        logger.warning("worker_started_without_bot_token_jobs")
    scheduler.start()
    logger.info("worker_started")

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown(wait=False)
        if bot is not None:
            await bot.session.close()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
