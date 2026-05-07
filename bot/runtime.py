from aiogram import Bot, Dispatcher

from bot.middleware import ErrorHandlerMiddleware, UserInjectMiddleware
from bot.handlers import build_router
from shared.config import Settings


def build_bot_runtime(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    # Register middleware — order matters: error handler wraps everything,
    # user inject runs inside so handler data has db_user/db_profile.
    dispatcher.message.middleware(ErrorHandlerMiddleware())
    dispatcher.callback_query.middleware(ErrorHandlerMiddleware())
    dispatcher.message.middleware(UserInjectMiddleware())
    dispatcher.callback_query.middleware(UserInjectMiddleware())

    dispatcher.include_router(build_router())
    return bot, dispatcher
