import asyncio
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from shared.config import get_settings
from shared.logging import configure_logging
from worker.tasks import deliver_law_updates, send_due_reminders, sync_user_events


logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    bot = Bot(token=settings.telegram_bot_token)
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    scheduler.add_job(sync_user_events, "cron", hour=settings.user_event_sync_hour, minute=0)
    scheduler.add_job(
        send_due_reminders,
        "interval",
        minutes=settings.reminder_dispatch_interval_minutes,
        kwargs={"bot": bot, "batch_size": settings.reminder_batch_size},
    )
    scheduler.add_job(
        deliver_law_updates,
        "interval",
        minutes=settings.law_fetch_interval_minutes,
        kwargs={"bot": bot, "min_importance": settings.law_min_importance_score},
    )
    scheduler.start()
    logger.info("worker_started")

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
