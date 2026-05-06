from aiogram import Bot, Dispatcher

from bot.middleware import ErrorHandlerMiddleware
from bot.handlers import build_router
from shared.config import Settings


def build_bot_runtime(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    # Register middleware
    dispatcher.message.middleware(ErrorHandlerMiddleware())
    dispatcher.callback_query.middleware(ErrorHandlerMiddleware())

    dispatcher.include_router(build_router())
    return bot, dispatcher
