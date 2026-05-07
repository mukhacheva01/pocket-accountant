"""Tests for bot.runtime."""

from bot.middleware import ErrorHandlerMiddleware, UserInjectMiddleware
from bot.runtime import build_bot_runtime
from shared.config import Settings


def _make_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
        TELEGRAM_BOT_TOKEN="123456:ABC",
    )


def test_build_bot_runtime():
    bot, dispatcher = build_bot_runtime(_make_settings())
    assert bot is not None
    assert dispatcher is not None


def test_error_middleware_registered():
    _, dispatcher = build_bot_runtime(_make_settings())
    msg_mw = [type(m) for m in dispatcher.message.middleware]
    cb_mw = [type(m) for m in dispatcher.callback_query.middleware]
    assert ErrorHandlerMiddleware in msg_mw
    assert ErrorHandlerMiddleware in cb_mw


def test_user_inject_middleware_registered():
    _, dispatcher = build_bot_runtime(_make_settings())
    msg_mw = [type(m) for m in dispatcher.message.middleware]
    cb_mw = [type(m) for m in dispatcher.callback_query.middleware]
    assert UserInjectMiddleware in msg_mw
    assert UserInjectMiddleware in cb_mw


def test_router_included():
    _, dispatcher = build_bot_runtime(_make_settings())
    assert len(dispatcher.sub_routers) > 0
