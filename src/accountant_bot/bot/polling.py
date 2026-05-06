import asyncio
import logging

from accountant_bot.bot.runtime import build_bot_runtime
from accountant_bot.core.config import get_settings
from accountant_bot.core.logging import configure_logging


logger = logging.getLogger(__name__)


async def run_polling() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    bot, dispatcher = build_bot_runtime(settings)

    # Polling mode does not require a public HTTPS webhook endpoint.
    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("bot_polling_started")

    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("bot_polling_stopped")


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
