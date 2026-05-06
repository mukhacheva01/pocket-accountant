from aiogram import Bot, Dispatcher

from accountant_bot.bot.middleware import ErrorHandlerMiddleware
from accountant_bot.bot.router import build_router
from accountant_bot.core.config import Settings


def build_bot_runtime(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    # Register middleware
    dispatcher.message.middleware(ErrorHandlerMiddleware())
    dispatcher.callback_query.middleware(ErrorHandlerMiddleware())

    dispatcher.include_router(build_router())
    return bot, dispatcher
