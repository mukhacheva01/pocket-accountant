from aiogram import Bot, Dispatcher

from bot.backend_client import BackendClient
from bot.middleware import ErrorHandlerMiddleware
from bot.handlers import build_router
from shared.config import Settings

_backend_client: BackendClient | None = None


def get_backend_client() -> BackendClient:
    global _backend_client
    if _backend_client is None:
        from shared.config import get_settings
        settings = get_settings()
        _backend_client = BackendClient(base_url=settings.app_base_url)
    return _backend_client


def build_bot_runtime(settings: Settings) -> tuple[Bot, Dispatcher]:
    global _backend_client
    _backend_client = BackendClient(base_url=settings.app_base_url)

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    dispatcher.message.middleware(ErrorHandlerMiddleware())
    dispatcher.callback_query.middleware(ErrorHandlerMiddleware())

    dispatcher.include_router(build_router())
    return bot, dispatcher
