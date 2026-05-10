"""Tests for bot.middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.middleware import ErrorHandlerMiddleware, UserInjectMiddleware
from tests.unit.bot_helpers import make_mock_backend_client


class TestErrorHandlerMiddleware:
    async def test_passes_through(self):
        mw = ErrorHandlerMiddleware()
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        result = await mw(handler, event, {})
        assert result == "ok"
        handler.assert_awaited_once()

    async def test_catches_exception_message(self):
        mw = ErrorHandlerMiddleware()
        handler = AsyncMock(side_effect=ValueError("boom"))
        event = MagicMock()
        event.chat = MagicMock(id=123)
        event.answer = AsyncMock()
        event.__class__.__name__ = "Message"
        from aiogram.types import Message
        event.__class__ = Message
        result = await mw(handler, event, {})
        assert result is None

    async def test_catches_exception_callback(self):
        mw = ErrorHandlerMiddleware()
        handler = AsyncMock(side_effect=ValueError("boom"))
        from aiogram.types import CallbackQuery
        event = MagicMock(spec=CallbackQuery)
        event.message = MagicMock()
        event.answer = AsyncMock()
        result = await mw(handler, event, {})
        assert result is None


class TestUserInjectMiddleware:
    async def test_injects_user_data(self):
        mw = UserInjectMiddleware()
        handler = AsyncMock(return_value="ok")

        mc = make_mock_backend_client()
        from aiogram.types import Message
        event = MagicMock(spec=Message)
        event.text = "/start"
        event.__class__ = Message

        actor = MagicMock()
        actor.id = 123
        actor.username = "tester"
        actor.first_name = "Тест"

        data = {"event_from_user": actor}

        with patch("bot.runtime.get_backend_client", return_value=mc):
            result = await mw(handler, event, data)

        assert result == "ok"
        mc.track_activity.assert_awaited_once()
        assert "db_user" in data

    async def test_skips_without_actor(self):
        mw = UserInjectMiddleware()
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        data = {}

        result = await mw(handler, event, data)
        assert result == "ok"
        handler.assert_awaited_once()

    async def test_handles_api_error(self):
        mw = UserInjectMiddleware()
        handler = AsyncMock(return_value="ok")

        mc = make_mock_backend_client()
        mc.track_activity = AsyncMock(side_effect=Exception("connection error"))

        from aiogram.types import Message
        event = MagicMock(spec=Message)
        event.text = "hello"
        event.__class__ = Message

        actor = MagicMock()
        actor.id = 123
        actor.username = "tester"
        actor.first_name = "Тест"

        data = {"event_from_user": actor}

        with patch("bot.runtime.get_backend_client", return_value=mc):
            result = await mw(handler, event, data)

        assert result == "ok"
        handler.assert_awaited_once()

    async def test_callback_event_type(self):
        mw = UserInjectMiddleware()
        handler = AsyncMock(return_value="ok")

        mc = make_mock_backend_client()
        from aiogram.types import CallbackQuery
        event = MagicMock(spec=CallbackQuery)
        event.data = "nav:home"
        event.__class__ = CallbackQuery

        actor = MagicMock()
        actor.id = 123
        actor.username = "tester"
        actor.first_name = "Тест"

        data = {"event_from_user": actor}

        with patch("bot.runtime.get_backend_client", return_value=mc):
            result = await mw(handler, event, data)

        assert result == "ok"
        mc.track_activity.assert_awaited_once()
        call_kwargs = mc.track_activity.call_args[1]
        assert call_kwargs["event_type"] == "callback"
